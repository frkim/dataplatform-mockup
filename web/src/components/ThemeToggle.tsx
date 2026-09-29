"use client";

import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import SettingsBrightnessIcon from "@mui/icons-material/SettingsBrightness";
import { IconButton, Tooltip } from "@mui/material";
import { useColorScheme } from "@mui/material/styles";

/** Toggle the persisted app color mode between system, light, and dark. */
export function ThemeToggle() {
  const { mode, setMode } = useColorScheme();
  const nextMode = mode === "dark" ? "light" : mode === "light" ? "system" : "dark";
  const label = `Switch color mode to ${nextMode}`;
  const Icon = mode === "dark" ? DarkModeIcon : mode === "light" ? LightModeIcon : SettingsBrightnessIcon;

  return (
    <Tooltip title={label}>
      <IconButton color="inherit" aria-label={label} onClick={() => setMode(nextMode)}>
        <Icon />
      </IconButton>
    </Tooltip>
  );
}
