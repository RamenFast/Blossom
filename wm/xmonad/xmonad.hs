--------------------------------------------------------------------------------
-- Blossom — xmonad
--
-- AMOLED true-black, pink focus border, gold for the window that wants you.
-- The theme thesis made structural: the accent IS the focused window's edge,
-- and the gaps are the void showing through.
--
-- Keys are mostly xmonad's defaults (which are already vim/LARBS-shaped — Super
-- mod, h/j/k/l), with a few additions. See the keys table in the repo README.
--------------------------------------------------------------------------------

import XMonad hiding ((|||))
import System.Exit (exitSuccess)
import qualified XMonad.StackSet as W

import XMonad.Hooks.EwmhDesktops (ewmh, ewmhFullscreen)
import XMonad.Hooks.ManageDocks (avoidStruts)
import XMonad.Hooks.ManageHelpers (isDialog, doCenterFloat)
import XMonad.Hooks.StatusBar (statusBarProp, withEasySB, defToggleStrutsKey)
import XMonad.Hooks.StatusBar.PP
import XMonad.Hooks.UrgencyHook (withUrgencyHook, NoUrgencyHook(..))

import XMonad.Layout.LayoutCombinators ((|||), JumpToLayout(..))
import XMonad.Layout.NoBorders (smartBorders)
import XMonad.Layout.Renamed (renamed, Rename(Replace))
import XMonad.Layout.Spacing (spacingRaw, Border(..))

import XMonad.Util.EZConfig (additionalKeysP)
import XMonad.Util.SpawnOnce (spawnOnce)

-- ---- Blossom palette -------------------------------------------------------
pink, pinkLt, gold, blue, dim, edge :: String
pink   = "#db3776"   -- focused / current
pinkLt = "#f060a0"   -- layout name
gold   = "#f1bf40"   -- urgent
blue   = "#eaf6ff"   -- text
dim    = "#9fb3c2"   -- inactive text
edge   = "#2a2e37"   -- unfocused border / separators

-- ---- knobs -----------------------------------------------------------------
myTerminal :: String
myTerminal = "kitty"

myModMask :: KeyMask
myModMask = mod4Mask          -- Super

myBorderWidth :: Dimension
myBorderWidth = 2

myGap :: Integer
myGap = 6

myWorkspaces :: [String]
myWorkspaces = map show [1 .. 9 :: Int]

dmenuCmd :: String
dmenuCmd = "dmenu_run -fn 'monospace-11' -nb '#000000' -nf '#eaf6ff' \
           \-sb '#db3776' -sf '#000000' -p ' '"

-- ---- layouts ---------------------------------------------------------------
-- master/stack, predictable: master on the left, new windows join the stack.
myLayout = avoidStruts . smartBorders . gaps $ (tall ||| wide ||| full)
  where
    gaps = spacingRaw False (Border myGap myGap myGap myGap) True
                            (Border myGap myGap myGap myGap) True
    tall = renamed [Replace "tall"] $ Tall 1 (3 / 100) (1 / 2)
    wide = renamed [Replace "wide"] $ Mirror (Tall 1 (3 / 100) (1 / 2))
    full = renamed [Replace "full"] Full

-- ---- where windows go ------------------------------------------------------
myManageHook = composeAll
  [ isDialog              --> doCenterFloat
  , className =? "Blossom"        --> doCenterFloat   -- the control GUI
  , className =? "Blossom-control.py" --> doCenterFloat
  , className =? "Gpick"          --> doCenterFloat
  , className =? "Xmessage"       --> doCenterFloat
  ]

-- ---- startup ---------------------------------------------------------------
myStartupHook = do
  spawnOnce "xsetroot -solid '#000000'"   -- the void
  spawnOnce "picom"                        -- harmless if not installed

-- ---- status bar formatting -------------------------------------------------
myPP :: PP
myPP = def
  { ppCurrent         = xmobarColor pink "" . wrap "[" "]"
  , ppVisible         = xmobarColor blue ""
  , ppHidden          = xmobarColor dim ""
  , ppHiddenNoWindows = xmobarColor edge ""
  , ppUrgent          = xmobarColor gold "" . wrap "!" "!"
  , ppTitle           = xmobarColor blue "" . shorten 70
  , ppLayout          = xmobarColor pinkLt ""
  , ppSep             = xmobarColor edge "" "  ·  "
  , ppWsSep           = " "
  }

-- ---- added keys (xmonad defaults already give h/j/k/l, workspaces, etc.) ----
myKeys :: [(String, X ())]
myKeys =
  [ ("M-<Return>",   spawn myTerminal)            -- terminal (Luke-style)
  , ("M-S-<Return>", windows W.swapMaster)        -- promote to master
  , ("M-d",          spawn dmenuCmd)              -- launcher
  , ("M-w",          spawn "x-www-browser")       -- browser
  , ("M-e",          spawn "nemo")                -- files
  , ("M-c",          spawn "setsid -f python3 $HOME/.themes/Blossom/tools/blossom-control.py")
  , ("M-f",          sendMessage $ JumpToLayout "full")   -- fullscreen layout
  , ("M-t",          sendMessage $ JumpToLayout "tall")
  , ("M-S-c",        kill)
  , ("<Print>",      spawn "gnome-screenshot -i")
  , ("M-S-x",        io exitSuccess)              -- leave xmonad
  -- media keys (EZConfig knows the XF86 names)
  , ("<XF86AudioRaiseVolume>", spawn "pactl set-sink-volume @DEFAULT_SINK@ +5%")
  , ("<XF86AudioLowerVolume>", spawn "pactl set-sink-volume @DEFAULT_SINK@ -5%")
  , ("<XF86AudioMute>",        spawn "pactl set-sink-mute @DEFAULT_SINK@ toggle")
  , ("<XF86MonBrightnessUp>",   spawn "xbacklight -inc 10")
  , ("<XF86MonBrightnessDown>", spawn "xbacklight -dec 10")
  ]

-- ---- assembly --------------------------------------------------------------
main :: IO ()
main = xmonad
     . ewmhFullscreen . ewmh
     . withUrgencyHook NoUrgencyHook
     . withEasySB (statusBarProp "xmobar ~/.config/xmobar/xmobarrc" (pure myPP))
                  defToggleStrutsKey
     $ myConfig

myConfig = def
  { modMask            = myModMask
  , terminal           = myTerminal
  , workspaces         = myWorkspaces
  , borderWidth        = myBorderWidth
  , normalBorderColor  = edge
  , focusedBorderColor = pink
  , layoutHook         = myLayout
  , manageHook         = myManageHook <+> manageHook def
  , startupHook        = myStartupHook
  } `additionalKeysP` myKeys
