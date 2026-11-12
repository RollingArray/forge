import { describe, expect, it } from 'vitest';
import {
  compareExactDecimals,
  isExactDecimalString,
} from './exact-decimal';

describe('exact-decimal', () => {
  it('validates decimal strings without converting them to Number', () => {
    expect(isExactDecimalString('12.3400')).toBe(true);
    expect(isExactDecimalString('-0.0001')).toBe(true);
    expect(isExactDecimalString('+12')).toBe(true);
    expect(isExactDecimalString('1e10000')).toBe(true);
    expect(isExactDecimalString('.25')).toBe(true);
    expect(isExactDecimalString('12.')).toBe(true);
  });

  it('rejects invalid and non-decimal strings', () => {
    expect(isExactDecimalString('')).toBe(false);
    expect(isExactDecimalString('abc')).toBe(false);
    expect(isExactDecimalString('1.2.3')).toBe(false);
    expect(isExactDecimalString('NaN')).toBe(false);
    expect(isExactDecimalString('Infinity')).toBe(false);
  });

  it('compares high-precision decimals exactly', () => {
    expect(
      compareExactDecimals(
        '0.100000000000000001',
        '0.100000000000000002',
      ),
    ).toBe(-1);
  });

  it('compares negative decimals exactly', () => {
    expect(compareExactDecimals('-10.01', '-10.02')).toBe(1);
    expect(compareExactDecimals('-0.1', '0')).toBe(-1);
  });

  it('treats trailing zeros as numerically equivalent', () => {
    expect(compareExactDecimals('12.3400', '12.34')).toBe(0);
  });

  it('compares exponent notation exactly', () => {
    expect(compareExactDecimals('1e10000', '9e9999')).toBe(1);
    expect(compareExactDecimals('1.2e-5', '0.000012')).toBe(0);
  });

  it('returns null for invalid comparison operands', () => {
    expect(compareExactDecimals('invalid', '1')).toBeNull();
  });
});
