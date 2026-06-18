// blossom-steam — paint the Steam client in Blossom (AMOLED black / pink / gold)
// over Steam's own CEF remote debugger. No sudo, no Millennium.
//
//   blossom-steam live     enable debugging if needed, then inject + keep every
//                          window themed (watches for new/navigated pages)
//   blossom-steam once     inject into the currently-open pages and exit
//   blossom-steam gen      regenerate generated.css from Steam's live stylesheets
//   blossom-steam enable    turn on CEF debugging + restart Steam
//
// Steam restores its steamui CSS from the client package on every launch, so a
// skin can't live in those files — it has to be injected at runtime. Millennium
// does that with a sudo'd bootstrap; this does it with the debugger Valve already
// ships (a localhost port, opt-in via ~/.steam/steam/.cef-enable-remote-debugging).

use serde_json::Value;
use std::collections::HashSet;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::process::Command;
use std::{fs, thread, time::Duration};
use tungstenite::{connect, Message};

const CSS_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/..");
const PORT: &str = "127.0.0.1:8080";

// --- the apply shim: (re)insert <style id=blossom-skin>, and re-append on load so
//     it stays last (wins) even when run at document-start via the Page domain. ---
const APPLY_A: &str = "(function(){var C=";
const APPLY_B: &str = ";function a(){var s=document.getElementById('blossom-skin');\
if(!s){s=document.createElement('style');s.id='blossom-skin';}s.textContent=C;\
(document.head||document.documentElement).appendChild(s);}a();\
if(document.readyState!=='complete'){document.addEventListener('DOMContentLoaded',a);addEventListener('load',a);}return 1;})()";

// --- the remap extractor (run in-page): every live rule that paints Steam's
//     accent blue or a structural grey, re-emitted in the Blossom palette. ------
const EXTRACT_JS: &str = r##"
(function () {
  var TRIPLETS = [
    [/\b26,\s*159,\s*255\b/g, '219, 55, 118'], [/\b25,\s*153,\s*255\b/g, '219, 55, 118'],
    [/\b103,\s*193,\s*245\b/g, '232, 90, 146'], [/\b102,\s*192,\s*244\b/g, '232, 90, 146'],
    [/\b61,\s*68,\s*80\b/g, '28, 28, 28'], [/\b14,\s*20,\s*27\b/g, '0, 0, 0'],
    [/\b23,\s*29,\s*37\b/g, '10, 10, 10'], [/\b27,\s*40,\s*56\b/g, '0, 0, 0'],
    [/\b42,\s*71,\s*94\b/g, '20, 20, 20'],
  ];
  var HEX = [
    [/#1a9fff/gi, '#db3776'], [/#1999ff/gi, '#db3776'], [/#67c1f5/gi, '#e85a92'],
    [/#66c0f4/gi, '#e85a92'], [/#3d4450/gi, '#1c1c1c'], [/#0e141b/gi, '#000000'],
    [/#171d25/gi, '#0a0a0a'], [/#1b2838/gi, '#000000'], [/#2a475e/gi, '#141414'],
  ];
  var GREY = /3d4450|61,\s*68,\s*80|0e141b|14,\s*20,\s*27|171d25|23,\s*29,\s*37|1b2838|27,\s*40,\s*56|2a475e|42,\s*71,\s*94/i;
  var BLUE = /1a9fff|1999ff|67c1f5|66c0f4|26,\s*159,\s*255|25,\s*153,\s*255|103,\s*193,\s*245|102,\s*192,\s*244/i;
  var GREY_OK = /^(background|border|box-shadow|outline|fill|stroke|--)/;
  var STATE = /:hover|:focus|\.gpfocus/i;   // interaction states -> pink wash
  function remap(v){TRIPLETS.forEach(function(p){v=v.replace(p[0],p[1]);});HEX.forEach(function(p){v=v.replace(p[0],p[1]);});return v;}
  var out=[], seen={}, nBlue=0, nGrey=0, nState=0;
  for(var i=0;i<document.styleSheets.length;i++){
    var rules; try{rules=document.styleSheets[i].cssRules;}catch(e){continue;}
    if(!rules)continue;
    for(var j=0;j<rules.length;j++){
      var r=rules[j]; if(r.type!==1||!r.style||!r.selectorText)continue;
      var decls=[];
      for(var k=0;k<r.style.length;k++){
        var prop=r.style[k], val=r.style.getPropertyValue(prop);
        var isBlue=BLUE.test(val), isGrey=GREY.test(val);
        if(!isBlue&&!isGrey)continue;
        if(isGrey&&!isBlue&&!GREY_OK.test(prop))continue;
        decls.push(prop+':'+remap(val)+' !important');
        if(isBlue)nBlue++; else nGrey++;
      }
      if(STATE.test(r.selectorText)){var bg=r.style.getPropertyValue('background-color');
        if(bg&&/rgb|#/.test(bg)&&!/url/.test(bg)){var w='background-color: rgba(219, 55, 118, 0.16) !important';
          if(decls.indexOf(w)<0){decls.push(w);nState++;}}}
      if(decls.length){var line=r.selectorText+'{'+decls.join(';')+'}';if(!seen[line]){seen[line]=1;out.push(line);}}
    }
  }
  return '/* blossom-steam: '+out.length+' rules ('+nBlue+' accent, '+nGrey+' surface, '+nState+' hover decls). Regenerate after Steam updates. */\n'+out.join('\n');
})()
"##;

fn http_get(path: &str) -> Option<String> {
    let mut s = TcpStream::connect(PORT).ok()?;
    s.set_read_timeout(Some(Duration::from_secs(3))).ok()?;
    // NB: CEF derives webSocketDebuggerUrl from this Host header — it MUST carry
    // the port, or the ws:// urls come back portless and unconnectable.
    write!(s, "GET {path} HTTP/1.1\r\nHost: {PORT}\r\nConnection: close\r\n\r\n").ok()?;
    // CEF keeps the socket open, so read_to_string would block; read until the
    // response is complete (by Content-Length / chunked terminator) or EOF.
    let (mut buf, mut tmp) = (Vec::new(), [0u8; 8192]);
    loop {
        if body_complete(&String::from_utf8_lossy(&buf)) { break; }
        match s.read(&mut tmp) {
            Ok(0) => break,
            Ok(n) => buf.extend_from_slice(&tmp[..n]),
            Err(_) => break, // timeout/err: use what we have
        }
    }
    let raw = String::from_utf8_lossy(&buf).into_owned();
    let split = raw.find("\r\n\r\n")?;
    let (head, body) = (raw[..split].to_lowercase(), &raw[split + 4..]);
    Some(if head.contains("transfer-encoding: chunked") { de_chunk(body) } else { body.to_string() })
}

fn body_complete(raw: &str) -> bool {
    let Some(split) = raw.find("\r\n\r\n") else { return false };
    let head = raw[..split].to_lowercase();
    let body = &raw[split + 4..];
    if let Some(cl) = head.lines().find_map(|l| l.strip_prefix("content-length:")) {
        if let Ok(n) = cl.trim().parse::<usize>() { return body.len() >= n; }
    }
    if head.contains("transfer-encoding: chunked") {
        return body.contains("\r\n0\r\n\r\n") || body.starts_with("0\r\n\r\n");
    }
    false // close-delimited: wait for EOF
}

fn de_chunk(body: &str) -> String {
    let (mut out, mut i, b) = (String::new(), 0usize, body.as_bytes());
    while i < b.len() {
        let nl = match body[i..].find("\r\n") { Some(p) => i + p, None => break };
        let size = usize::from_str_radix(body[i..nl].trim(), 16).unwrap_or(0);
        if size == 0 { break; }
        let start = nl + 2;
        let end = (start + size).min(b.len());
        out.push_str(&body[start..end]);
        i = end + 2;
    }
    out
}

fn debugger_up() -> bool { http_get("/json/version").is_some() }

fn pages() -> Vec<Value> {
    http_get("/json")
        .and_then(|b| serde_json::from_str::<Value>(b.trim()).ok())
        .and_then(|v| v.as_array().cloned())
        .unwrap_or_default()
}

/// Send one Runtime.evaluate; return the string result if `want` is set.
fn ws_eval(ws_url: &str, expr: &str, want: bool) -> Option<String> {
    let (mut sock, _) = connect(ws_url).ok()?;
    let req = serde_json::json!({
        "id": 1, "method": "Runtime.evaluate",
        "params": {"expression": expr, "returnByValue": want}
    });
    sock.send(Message::Text(req.to_string())).ok()?;
    for _ in 0..64 {
        if let Ok(Message::Text(t)) = sock.read() {
            if let Ok(v) = serde_json::from_str::<Value>(&t) {
                if v["id"] == 1 {
                    let _ = sock.close(None);
                    return if want {
                        v["result"]["result"]["value"].as_str().map(str::to_string)
                    } else { Some(String::new()) };
                }
            }
        } else { break; }
    }
    None
}

fn skin_css() -> String {
    let read = |f: &str| fs::read_to_string(format!("{CSS_DIR}/{f}")).unwrap_or_default();
    format!("{}\n{}", read("webkit.css"), read("generated.css"))
}

fn inject_all() -> usize {
    let css = serde_json::to_string(&skin_css()).unwrap();
    let js = format!("{APPLY_A}{css}{APPLY_B}");
    let ps = pages();
    if std::env::var("BLOSSOM_DEBUG").is_ok() {
        eprintln!("[dbg] pages={} types={:?}", ps.len(),
            ps.iter().map(|p| p["type"].as_str().unwrap_or("?")).collect::<Vec<_>>());
        if let Some(u) = ps.iter().find_map(|p| p["webSocketDebuggerUrl"].as_str()) {
            eprintln!("[dbg] first ws={u} -> eval={:?}", ws_eval(u, "1+1", true));
        }
    }
    ps.iter()
        .filter(|p| p["type"] == "page")
        .filter_map(|p| p["webSocketDebuggerUrl"].as_str())
        .filter(|u| ws_eval(u, &js, false).is_some())
        .count()
}

fn main_page_ws() -> Option<String> {
    let ps = pages();
    ps.iter()
        .find(|p| p["title"] == "Steam" && p["url"].as_str().unwrap_or("").contains("minwidth=1010"))
        .or_else(|| ps.iter().find(|p| p["url"].as_str().unwrap_or("").contains("steamloopback")))
        .and_then(|p| p["webSocketDebuggerUrl"].as_str().map(str::to_string))
}

/// Event-driven theming: attach to the browser target, discover every page the
/// moment it's created, and register a document-start inject so a window is
/// themed before it paints and never flashes on navigation. One persistent
/// connection — no polling. Returns on connection drop (e.g. Steam restart).
fn run_session() -> Option<()> {
    let ver = http_get("/json/version")?;
    let burl = serde_json::from_str::<Value>(ver.trim()).ok()?
        ["webSocketDebuggerUrl"].as_str()?.to_string();
    let (mut sock, _) = connect(&burl).ok()?;
    let css = serde_json::to_string(&skin_css()).ok()?;
    let apply = format!("{APPLY_A}{css}{APPLY_B}");
    let mut id: i64 = 0;
    macro_rules! send {
        ($v:expr) => {{ id += 1; let mut m = $v; m["id"] = id.into();
            sock.send(Message::Text(m.to_string())).ok()?; }};
    }
    send!(serde_json::json!({"method": "Target.setDiscoverTargets", "params": {"discover": true}}));

    let mut seen: HashSet<String> = HashSet::new();
    loop {
        let txt = match sock.read() {
            Ok(Message::Text(t)) => t,
            Ok(Message::Ping(p)) => { sock.send(Message::Pong(p)).ok(); continue; }
            Ok(Message::Close(_)) | Err(_) => return None,
            Ok(_) => continue,
        };
        let m: Value = match serde_json::from_str(&txt) { Ok(x) => x, Err(_) => continue };
        match m["method"].as_str() {
            Some("Target.targetCreated") | Some("Target.targetInfoChanged") => {
                let ti = &m["params"]["targetInfo"];
                if ti["type"] == "page" {
                    if let Some(tid) = ti["targetId"].as_str() {
                        if seen.insert(tid.to_string()) {
                            send!(serde_json::json!({"method": "Target.attachToTarget",
                                "params": {"targetId": tid, "flatten": true}}));
                        }
                    }
                }
            }
            Some("Target.attachedToTarget") => {
                if let Some(sid) = m["params"]["sessionId"].as_str().map(str::to_string) {
                    send!(serde_json::json!({"sessionId": sid, "method": "Page.enable"}));
                    send!(serde_json::json!({"sessionId": sid, "method": "Page.addScriptToEvaluateOnNewDocument",
                        "params": {"source": apply}}));
                    send!(serde_json::json!({"sessionId": sid, "method": "Runtime.evaluate",
                        "params": {"expression": apply}}));
                }
            }
            _ => {}
        }
    }
}

fn live_event() {
    ensure_marker();
    println!("❀ Blossom live — theming every window the instant it opens (Ctrl-C to stop)");
    loop {
        if debugger_up() { let _ = run_session(); }
        thread::sleep(Duration::from_secs(2)); // (re)connect after a Steam restart
    }
}

fn ensure_marker() {
    let marker = format!("{}/.steam/steam/.cef-enable-remote-debugging", std::env::var("HOME").unwrap());
    let _ = fs::OpenOptions::new().create(true).append(true).open(&marker);
}

fn enable_and_restart() {
    ensure_marker();
    let marker = format!("{}/.steam/steam/.cef-enable-remote-debugging", std::env::var("HOME").unwrap());
    println!("  ✓ {marker}");
    let _ = Command::new("steam").arg("-shutdown").status();
    for _ in 0..60 {
        if Command::new("pgrep").args(["-x", "steam"]).status().map(|s| !s.success()).unwrap_or(true) { break; }
        thread::sleep(Duration::from_millis(500));
    }
    thread::sleep(Duration::from_secs(2));
    let _ = Command::new("steam").stdout(std::process::Stdio::null()).stderr(std::process::Stdio::null()).spawn();
    print!("  restarting Steam");
    for _ in 0..120 {
        if debugger_up() { println!("  ✓ debugger up"); return; }
        print!("."); let _ = std::io::stdout().flush();
        thread::sleep(Duration::from_secs(1));
    }
    println!("\n  ! debugger never came up");
}

fn main() {
    let cmd = std::env::args().nth(1).unwrap_or_else(|| "live".into());
    match cmd.as_str() {
        "enable" => enable_and_restart(),
        "gen" => {
            if !debugger_up() { eprintln!("debugger down — run: blossom-steam enable"); std::process::exit(1); }
            let ws = main_page_ws().expect("no main Steam window page");
            let css = ws_eval(&ws, EXTRACT_JS, true).expect("extract failed");
            let path = format!("{CSS_DIR}/generated.css");
            fs::write(&path, &css).unwrap();
            println!("✓ wrote {path}\n  {}", css.lines().next().unwrap_or(""));
        }
        "once" => {
            if !debugger_up() { eprintln!("debugger down — run: blossom-steam enable"); std::process::exit(1); }
            println!("✓ injected into {} page(s)", inject_all());
        }
        "live" => live_event(),
        _ => eprintln!("usage: blossom-steam [live|once|gen|enable]"),
    }
}
