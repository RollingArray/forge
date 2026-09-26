import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-pattern-generator',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './pattern-generator.component.html',
  styleUrl: './pattern-generator.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PatternGeneratorComponent {
  readonly pattern = input('');
  readonly showValidation = input(false);

  readonly patternChange = output<string>();

  readonly tokens = [
    {
      symbol: '#',
      meaning: 'Digit',
      example: '0 1 2 3 4 5 6 7 8 9',
    },
    {
      symbol: 'A',
      meaning: 'Uppercase letter',
      example: 'A B C D ... Z',
    },
    {
      symbol: 'a',
      meaning: 'Lowercase letter',
      example: 'a b c d ... z',
    },
    {
      symbol: 'X',
      meaning: 'Alphanumeric',
      example: 'A 7 x 9 B',
    },
  ];

  updatePattern(value: string): void {
    this.patternChange.emit(value);
  }

  previewPattern(pattern: string): string {
    const value = pattern.trim();

    if (!value) {
      return 'Enter a pattern above';
    }

    let seed = 0;

    for (let index = 0; index < value.length; index += 1) {
      seed = (seed * 31 + value.charCodeAt(index)) >>> 0;
    }

    const nextRandom = (): number => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };

    const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const lowercase = 'abcdefghijklmnopqrstuvwxyz';
    const digits = '0123456789';
    const alphanumeric = uppercase + lowercase + digits;

    return Array.from(value)
      .map((character) => {
        if (character === '#') {
          return digits[Math.floor(nextRandom() * digits.length)];
        }

        if (character === 'A') {
          return uppercase[Math.floor(nextRandom() * uppercase.length)];
        }

        if (character === 'a') {
          return lowercase[Math.floor(nextRandom() * lowercase.length)];
        }

        if (character === 'X') {
          return alphanumeric[
            Math.floor(nextRandom() * alphanumeric.length)
          ];
        }

        return character;
      })
      .join('');
  }
}
