import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  signal,
} from '@angular/core';

import { SpecificationValidationResult } from '../../../../core/interfaces/specification-validation.interface';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import {
  WorkspaceTableToolbarComponent,
  WorkspaceToolbarFilter,
} from '../../../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';

export type ValidationFilter = 'all' | 'error' | 'warning' | 'passed';

@Component({
  selector: 'app-model-validation-findings',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceScrollAreaComponent,
    WorkspaceTableToolbarComponent,
  ],
  templateUrl: './model-validation-findings.component.html',
  styleUrl: './model-validation-findings.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelValidationFindingsComponent {
  readonly validation =
    input.required<SpecificationValidationResult>();

  readonly activeFilter = signal<ValidationFilter>('all');
  readonly searchQuery = signal('');

  readonly toolbarFilters = computed<WorkspaceToolbarFilter[]>(() => [
    {
      id: 'all',
      label: 'All',
      icon: 'fact_check',
      count: this.filterCount('all'),
      active: this.activeFilter() === 'all',
    },
    {
      id: 'error',
      label: 'Errors',
      icon: 'error',
      count: this.filterCount('error'),
      active: this.activeFilter() === 'error',
      variant: 'danger',
    },
    {
      id: 'warning',
      label: 'Warnings',
      icon: 'warning',
      count: this.filterCount('warning'),
      active: this.activeFilter() === 'warning',
      variant: 'warning',
    },
    {
      id: 'passed',
      label: 'Passed',
      icon: 'check_circle',
      count: this.filterCount('passed'),
      active: this.activeFilter() === 'passed',
      variant: 'success',
    },
  ]);

  readonly filteredFindings = computed(() => {
    const findings = this.validation().findings;
    const filter = this.activeFilter();
    const query = this.searchQuery().trim().toLowerCase();

    return findings.filter((finding) => {
      const matchesFilter =
        filter === 'all' || finding.severity === filter;

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
    });
  });

  updateSearch(event: Event): void {
    this.searchQuery.set(
      (event.target as HTMLInputElement).value,
    );
  }

  clearSearch(): void {
    this.searchQuery.set('');
  }

  setFilter(filter: string): void {
    if (
      filter === 'all' ||
      filter === 'error' ||
      filter === 'warning' ||
      filter === 'passed'
    ) {
      this.activeFilter.set(filter);
    }
  }

  filterCount(filter: ValidationFilter): number {
    const findings = this.validation().findings;

    if (filter === 'all') {
      return findings.length;
    }

    return findings.filter(
      (finding) => finding.severity === filter,
    ).length;
  }
}
