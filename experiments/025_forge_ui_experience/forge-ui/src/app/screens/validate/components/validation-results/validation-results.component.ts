import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  signal,
} from '@angular/core';

import {
  ValidationFinding,
  ValidationSeverity,
} from '../../models/validate.models';

@Component({
  selector: 'app-validation-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './validation-results.component.html',
  styleUrl: './validation-results.component.css',
})
export class ValidationResultsComponent {
  readonly findings =
    input.required<readonly ValidationFinding[]>();

  readonly filter =
    signal<'all' | ValidationSeverity>('all');

  readonly search =
    signal('');

  readonly filteredFindings =
    computed(() => {
      const query =
        this.search()
          .trim()
          .toLowerCase();

      return this.findings().filter(
        finding => {
          const matchesFilter =
            this.filter() === 'all' ||
            finding.severity ===
              this.filter();

          if (!matchesFilter) {
            return false;
          }

          if (!query) {
            return true;
          }

          return [
            finding.category,
            finding.title,
            finding.details,
            finding.entity ?? '',
            finding.field ?? '',
          ]
            .join(' ')
            .toLowerCase()
            .includes(query);
        },
      );
    });

  count(
    severity: ValidationSeverity,
  ): number {
    return this.findings().filter(
      finding =>
        finding.severity === severity,
    ).length;
  }

  selectFilter(
    filter: 'all' | ValidationSeverity,
  ): void {
    this.filter.set(filter);
  }

  updateSearch(
    event: Event,
  ): void {
    this.search.set(
      (
        event.target as HTMLInputElement
      ).value,
    );
  }
}
