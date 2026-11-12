interface ParsedDecimal {
  sign: -1 | 0 | 1;
  digits: string;
  exponent: bigint;
}

function parseDecimal(value: string): ParsedDecimal | null {
  const text = value.trim();
  const match = /^([+-]?)(\d+(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d+))?$/.exec(text);

  if (!match) {
    return null;
  }

  const signText = match[1];
  const mantissa = match[2];
  const exponentText = match[3] ?? '0';

  const parts = mantissa.split('.');
  let digits = parts.join('').replace(/^0+/, '');
  let exponent: bigint;

  try {
    exponent = BigInt(exponentText) - BigInt(parts[1]?.length ?? 0);
  } catch {
    return null;
  }

  if (!digits) {
    return { sign: 0, digits: '0', exponent: 0n };
  }

  while (digits.endsWith('0')) {
    digits = digits.slice(0, -1);
    exponent += 1n;
  }

  return {
    sign: signText === '-' ? -1 : 1,
    digits,
    exponent,
  };
}

export function isExactDecimalString(value: string): boolean {
  return parseDecimal(value) !== null;
}

export function compareExactDecimals(
  left: string,
  right: string,
): -1 | 0 | 1 | null {
  const a = parseDecimal(left);
  const b = parseDecimal(right);

  if (!a || !b) {
    return null;
  }

  if (a.sign !== b.sign) {
    return a.sign < b.sign ? -1 : 1;
  }

  if (a.sign === 0) {
    return 0;
  }

  const aMagnitude = BigInt(a.digits.length) + a.exponent;
  const bMagnitude = BigInt(b.digits.length) + b.exponent;

  let absoluteComparison: -1 | 0 | 1;

  if (aMagnitude !== bMagnitude) {
    absoluteComparison = aMagnitude < bMagnitude ? -1 : 1;
  } else {
    const length = Math.max(a.digits.length, b.digits.length);
    const aDigits = a.digits.padEnd(length, '0');
    const bDigits = b.digits.padEnd(length, '0');

    absoluteComparison =
      aDigits === bDigits ? 0 : aDigits < bDigits ? -1 : 1;
  }

  return a.sign === 1
    ? absoluteComparison
    : absoluteComparison === 0
      ? 0
      : absoluteComparison === 1
        ? -1
        : 1;
}
