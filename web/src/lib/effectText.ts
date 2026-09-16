export function formatNumber(value: number): string {
  return String(Number.isInteger(value) ? value : Number(value.toFixed(2)));
}

export function signed(value: number): string {
  const text = formatNumber(value);
  return value >= 0 ? `+${text}` : text;
}

/** Fill %+n, %n, %+n%, %n% and %-n% with the value; append the value when there is no placeholder. */
export function formatEffect(description: string | null, key: string, value: number): string {
  if (!description) return `${key} (${signed(value)})`;
  let substituted = false;
  const text = description.replace(/%([+-]?)n(%?)/g, (_match, sign: string, percent: string) => {
    substituted = true;
    return (sign === "+" ? signed(value) : formatNumber(value)) + percent;
  });
  return substituted ? text : `${description} (${signed(value)})`;
}

export function scopeLabel(scope: string | null): string | null {
  return scope ? scope.replace(/_/g, " ") : null;
}
