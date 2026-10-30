/**
 * File: sidebar.component.ts
 * Purpose: Shared, route-aware FORGE authenticated navigation sidebar.
 */

import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  output,
  signal,
} from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { NavigationEnd, Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { WorkspaceService } from '../../../../core/services/workspace.service';
import { filter } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { QuickActionsComponent } from '../../../../features/workspace/components/quick-actions/quick-actions.component';
import { UserProfileComponent } from '../../../../shared/components/user-profile/user-profile.component';
import { ExecutionSelectorDialogComponent } from '../../../../shared/components/execution-selector-dialog/execution-selector-dialog.component';
import {
  WorkspaceNavigationGroup,
  WorkspaceNavigationGroupComponent,
} from '../workspace-navigation-group/workspace-navigation-group.component';

@Component({
  selector: 'app-forge-sidebar',
  standalone: true,
  imports: [
    DatePipe,
    DecimalPipe,
    QuickActionsComponent,
    UserProfileComponent,
    WorkspaceNavigationGroupComponent,
    ExecutionSelectorDialogComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css',
})
export class SidebarComponent {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly authService = inject(AuthService);
  private readonly workspaceService = inject(WorkspaceService);

  private readonly sessionUser = this.authService.getSession()?.user;



  readonly currentDataModelName = signal<string | null>(null);
  readonly currentDataModelDescription = signal<string | null>(null);

  readonly userDisplayName = signal(this.sessionUser?.displayName || 'Signed-in User');

  readonly userInitials = signal(this.getUserInitials(this.sessionUser?.displayName || 'User'));

  readonly isProfileModalOpen = signal(false);
  readonly isExecutionSelectorOpen = signal(false);
  readonly executionSelectorDestination = signal<
    'executions' | 'generated-data' | 'quality-analysis' | 'validation-analysis'
  >('executions');

  readonly workspaceNavigationGroups: readonly WorkspaceNavigationGroup[] = [
    {
      title: 'CREATE & BUILD',
      icon: 'construction',
      items: [
        {
          label: 'Create Data Model',
          icon: 'add_circle',
          action: 'create-data-model',
        },
        {
          label: 'Templates',
          icon: 'dashboard_customize',
          action: '',
          availability: 'soon',
        },
        {
          label: 'Import Model',
          icon: 'upload_file',
          action: '',
          availability: 'soon',
        },
      ],
    },
    {
      title: 'EXECUTION & MONITORING',
      icon: 'account_tree',
      items: [
        {
          label: 'Executions',
          icon: 'play_circle',
          action: 'executions',
        },
        {
          label: 'Generated Data',
          icon: 'database',
          action: 'generated-data',
        },
        {
          label: 'Quality Analysis',
          icon: 'monitoring',
          action: 'quality-analysis',
        },
        {
          label: 'Validation Analysis',
          icon: 'fact_check',
          action: 'validation-analysis',
        },
      ],
    },
    {
      title: 'RESOURCES',
      icon: 'folder_open',
      items: [
        {
          label: 'Favorites',
          icon: 'star',
          action: 'favorites',
        },
        {
          label: 'Activity Feed',
          icon: 'history',
          action: 'activity-feed',
        },
      ],
    },
    {
      title: 'ADMINISTRATION',
      icon: 'admin_panel_settings',
      items: [
        {
          label: 'People & Access',
          icon: 'group',
          action: '',
          availability: 'soon',
        },
        {
          label: 'Workspace Settings',
          icon: 'settings',
          action: '',
          availability: 'soon',
        },
      ],
    },
    {
      title: 'HELP & SUPPORT',
      icon: 'help',
      items: [
        {
          label: 'Help & Documentation',
          icon: 'menu_book',
          action: 'help',
        },
      ],
    },
  ];

  readonly dataModelNavigationGroup: WorkspaceNavigationGroup = {
    title: 'DATA MODEL',
    icon: 'account_tree',
    items: [
      { label: 'Model Studio', icon: 'account_tree', action: 'model-studio' },
      { label: 'Validation', icon: 'verified', action: 'validation' },
      { label: 'Population Plan', icon: 'groups', action: 'population' },
      { label: 'Generate', icon: 'auto_awesome', action: 'generate' },
      { label: 'Results', icon: 'dataset', action: 'results' },
    ],
  };

  readonly dataModelSupportingGroups = this.workspaceNavigationGroups.filter(
    (group) => !['CREATE & BUILD', 'ADMINISTRATION'].includes(group.title),
  );

  private getUserInitials(name: string): string {
    const profile = this.sessionUser?.profile;
    const nested =
      profile?.['ad_profile'] &&
      typeof profile['ad_profile'] === 'object' &&
      !Array.isArray(profile['ad_profile'])
        ? (profile['ad_profile'] as Record<string, unknown>)
        : profile;

    const firstName = typeof nested?.['firstName'] === 'string' ? nested['firstName'].trim() : '';
    const lastName = typeof nested?.['lastName'] === 'string' ? nested['lastName'].trim() : '';

    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase();
    }

    // Handle directory display names such as "Sen, Ranjoy (IND)".
    if (name.includes(',')) {
      const [surname, ...givenParts] = name.split(',');
      const givenName = givenParts.join(',').trim().split(/\\s+/)[0] ?? '';
      return `${givenName[0] ?? ''}${surname.trim()[0] ?? ''}`.toUpperCase() || '?';
    }

    const parts = name.trim().split(/\\s+/).filter(Boolean);

    if (parts.length > 1) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }

    if (firstName || lastName) {
      return `${firstName[0] ?? ''}${lastName[0] ?? ''}`.toUpperCase();
    }

    return name.trim().slice(0, 2).toUpperCase() || '?';
  }

  readonly action = output<string>();
  readonly currentUrl = signal(this.router.url);

  constructor() {
    this.loadCurrentDataModelIdentity();

    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((event) => {
        this.currentUrl.set(event.urlAfterRedirects);
        this.loadCurrentDataModelIdentity();
      });
  }

  private loadCurrentDataModelIdentity(): void {
    const segments = this.router.url.split('?')[0].split('#')[0].split('/').filter(Boolean);
    const workspaceIndex = segments.indexOf('workspace');
    const dataModelId = workspaceIndex >= 0 ? segments[workspaceIndex + 1] : undefined;

    if (!dataModelId || dataModelId === 'ui-kit-design-system') {
      this.currentDataModelName.set(null);
      this.currentDataModelDescription.set(null);
      return;
    }

    this.workspaceService.getDataModels().subscribe({
      next: (models) => {
        const model = models.find((item) => item.dataModelId === dataModelId);
        this.currentDataModelName.set(model?.name ?? null);
        this.currentDataModelDescription.set(model?.description?.trim() || null);
      },
      error: () => {
        this.currentDataModelName.set(null);
        this.currentDataModelDescription.set(null);
      },
    });
  }

  openExecutionSelector(
    destination:
      | 'executions'
      | 'generated-data'
      | 'quality-analysis'
      | 'validation-analysis',
  ): void {
    this.executionSelectorDestination.set(destination);
    this.isExecutionSelectorOpen.set(true);
  }

  confirmExecutionSelection(selection: {
    dataModelId: string;
    jobId: string;
    destination: 'executions' | 'generated-data' | 'quality-analysis' | 'validation-analysis';
  }): void {
    const { dataModelId, jobId, destination } = selection;
    const route =
      destination === 'executions'
        ? ['workspace', dataModelId, 'data-model', 'generate', jobId]
        : destination === 'generated-data'
          ? ['workspace', dataModelId, 'data-model', 'results', jobId]
          : destination === 'quality-analysis'
            ? [
                'workspace',
                dataModelId,
                'data-model',
                'results',
                jobId,
                'quality-analysis',
              ]
            : [
                'workspace',
                dataModelId,
                'data-model',
                'results',
                jobId,
                'validation-analysis',
              ];

    this.isExecutionSelectorOpen.set(false);
    void this.router.navigate(route);
  }

  isWorkspaceContext(): boolean {
    const url = this.currentUrl().split('?')[0].split('#')[0];
    return (
      url === '/workspace' ||
      url === '/workspace/favorites' ||
      url === '/workspace/activity' ||
      url === '/workspace/ui-kit-design-system' ||
      url === '/help'
    );
  }

  isDataModelContext(): boolean {
    const segments = this.currentUrl().split('?')[0].split('#')[0].split('/').filter(Boolean);

    return (
      segments[0] === 'workspace' && segments.length >= 3 && segments[1] !== 'ui-kit-design-system'
    );
  }

  isActive(section: string): boolean {
    const url = this.currentUrl().split('?')[0].split('#')[0];
    const segments = url.split('/').filter(Boolean);

    switch (section) {
      case 'workspace':
        return url === '/workspace' || url === '/workspace/ui-kit-design-system';

      case 'help':
        return segments.includes('help');

      case 'favorites':
        return url === '/workspace/favorites';

      case 'activity-feed':
        return url === '/workspace/activity';

      case 'model-studio':
        return segments.at(-1) === 'model-studio';

      case 'validation':
        return segments.at(-1) === 'model-validation';

      case 'population':
        return segments.at(-1) === 'population';

      case 'generate':
        return segments.includes('generate');

      case 'results':
      case 'generated-data':
        return (
          segments.includes('results') &&
          !segments.includes('quality-analysis') &&
          !segments.includes('validation-analysis')
        );

      case 'executions':
        return (
          segments.includes('generate') &&
          segments.at(-1) !== 'generate'
        );

      case 'quality-analysis':
        return segments.includes('quality-analysis');

      case 'validation-analysis':
        return segments.includes('validation-analysis');

      default:
        return false;
    }
  }

  select(action: string): void {

    const url = this.currentUrl().split('?')[0].split('#')[0];
    const segments = url.split('/').filter(Boolean);
    const workspaceIndex = segments.indexOf('workspace');
    const dataModelId = workspaceIndex >= 0 ? segments[workspaceIndex + 1] : undefined;

    switch (action) {
      case 'help':
        void this.router.navigate(['/help']);
        break;

      case 'workspace':
      case 'data-models':
        void this.router.navigate(['/workspace']);
        break;

      case 'favorites':
        void this.router.navigate(['/workspace/favorites']);
        break;

      case 'create-data-model':
        void this.router.navigate(['/workspace'], {
          queryParams: { quickAction: 'new-dataModel' },
        });
        break;
      case 'templates':
        void this.router.navigate(['/workspace'], {
          fragment: 'templates',
        });
        break;

      case 'activity-feed':
        void this.router.navigate(['/workspace/activity']);
        break;

      case 'model-studio':
        if (dataModelId && dataModelId !== 'ui-kit-design-system') {
          void this.router.navigate(['/workspace', dataModelId, 'model-studio']);
        }
        break;

      case 'validation':
        if (dataModelId && dataModelId !== 'ui-kit-design-system') {
          void this.router.navigate(['/workspace', dataModelId, 'model-validation']);
        }
        break;

      case 'population':
        if (dataModelId && dataModelId !== 'ui-kit-design-system') {
          void this.router.navigate(['/workspace', dataModelId, 'data-model', 'population']);
        }
        break;

      case 'generate':
        if (dataModelId && dataModelId !== 'ui-kit-design-system') {
          void this.router.navigate(['/workspace', dataModelId, 'data-model', 'generate']);
        }
        break;

      case 'executions':
      case 'generated-data':
      case 'quality-analysis':
      case 'validation-analysis':
        this.openExecutionSelector(action);
        break;

      case 'results': {
        const resultsIndex = segments.indexOf('results');
        const generateIndex = segments.indexOf('generate');
        const jobId =
          resultsIndex >= 0
            ? segments[resultsIndex + 1]
            : generateIndex >= 0
              ? segments[generateIndex + 1]
              : undefined;

        if (dataModelId && dataModelId !== 'ui-kit-design-system' && jobId) {
          void this.router.navigate(['/workspace', dataModelId, 'data-model', 'results', jobId]);
        }
        break;
      }

      default:
        this.action.emit(action);
        break;
    }
  }
}
