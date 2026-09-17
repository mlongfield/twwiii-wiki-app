/** Display rules for raw game values. Each returns the text to show, or null to hide the row. */
import { formatNumber } from "./effectText";

export type GameValueFormat = (value: number) => string | null;

export const formatRange: GameValueFormat = (v) => (v < 0 ? "∞" : v === 0 ? null : formatNumber(v));
export const formatDuration: GameValueFormat = (v) => (v <= 0 ? "∞" : `${formatNumber(v)}s`);
export const formatUses: GameValueFormat = (v) => (v < 0 ? null : formatNumber(v));
export const hideIfZero: GameValueFormat = (v) => (v === 0 ? null : formatNumber(v));
