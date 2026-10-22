import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  OnDestroy,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { Activity } from '../../core/interfaces/activity.interface';
import { WorkspaceService } from '../../core/services/workspace.service';
import { ActivityItemComponent } from '../workspace/components/recent-activity/activity-item/activity-item.component';
import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';
import { WorkflowContentComponent } from '../../shared/components/workflow-content/workflow-content.component';
import { ContentCardComponent } from '../../shared/components/content-card/content-card.component';

@Component({
  selector: 'app-activity-feed',
  standalone: true,
  imports: [
    ActivityItemComponent,
    WorkflowPageHeaderComponent,
    WorkflowContentComponent,
    ContentCardComponent,
  ],
  templateUrl: './activity-feed.component.html',
  styleUrl: './activity-feed.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActivityFeedComponent implements AfterViewInit, OnDestroy {
  private readonly workspaceService = inject(WorkspaceService);
  private readonly destroyRef = inject(DestroyRef);
  private observer: IntersectionObserver | null = null;

  @ViewChild('feedSentinel')
  private feedSentinel?: ElementRef<HTMLElement>;

  readonly activities = signal<Activity[]>([]);
  readonly loading = signal(false);
  readonly loadingMore = signal(false);
  readonly hasMore = signal(true);
  readonly error = signal<string | null>(null);

  private readonly pageSize = 25;
  private offset = 0;

  constructor() {
    this.loadFirstPage();
  }

  ngAfterViewInit(): void {
    if (typeof IntersectionObserver === 'undefined') {
      return;
    }

    this.observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          this.loadNextPage();
        }
      },
      { rootMargin: '240px 0px' },
    );

    if (this.feedSentinel) {
      this.observer.observe(this.feedSentinel.nativeElement);
    }
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  retry(): void {
    this.error.set(null);

    if (this.activities().length === 0) {
      this.loadFirstPage();
      return;
    }

    this.loadNextPage();
  }

  private loadFirstPage(): void {
    if (this.loading()) {
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    this.offset = 0;

    this.workspaceService
      .getActivityPage(0, this.pageSize)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.activities.set(page.activities);
          this.offset = page.offset + page.activities.length;
          this.hasMore.set(page.hasMore);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('The activity feed could not be loaded. Please try again.');
          this.loading.set(false);
        },
      });
  }

  private loadNextPage(): void {
    if (
      this.loading() ||
      this.loadingMore() ||
      !this.hasMore() ||
      this.error()
    ) {
      return;
    }

    this.loadingMore.set(true);
    this.error.set(null);

    this.workspaceService
      .getActivityPage(this.offset, this.pageSize)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.activities.update((current) => [...current, ...page.activities]);
          this.offset = page.offset + page.activities.length;
          this.hasMore.set(page.hasMore);
          this.loadingMore.set(false);
        },
        error: () => {
          this.error.set('More activity could not be loaded. Please try again.');
          this.loadingMore.set(false);
        },
      });
  }
}
