import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import {
  GenerationActivityEvent,
  GenerationSemanticCallProgressEvent,
} from '../../../features/generate/models/generation.models';

@Component({
  selector: 'app-generation-activity',
  standalone: true,
  templateUrl: './generation-activity.component.html',
  styleUrl: './generation-activity.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationActivityComponent {
  readonly activities = input<GenerationActivityEvent[]>([]);
  readonly isGenerating = input(false);
  readonly activeSemanticCall = input<GenerationSemanticCallProgressEvent | null>(null);

  visibleActivities(): GenerationActivityEvent[] {
    return this.activities()
      .filter((activity) => activity.stage !== 'FIELD_GENERATION')
      .slice()
      .reverse();
  }

  isActive(activity: GenerationActivityEvent): boolean {
    return activity.status === 'STARTED';
  }

  activityMessage(activity: GenerationActivityEvent): string {
    const entity = this.entityLabel(activity);
    const field = this.fieldLabel(activity);

    switch (activity.stage) {
      case 'SEMANTIC_GENERATION':
        return this.semanticMessage(activity, entity, field);

      case 'ENTITY_GENERATION':
        return activity.status === 'STARTED'
          ? `Creating ${entity} data`
          : `${entity} generation completed`;

      case 'CHUNK_GENERATION':
        return activity.status === 'STARTED'
          ? `Preparing ${entity} data batch ${activity.chunk_number ?? ''}`.trim()
          : `${entity} data batch ${activity.chunk_number ?? ''} completed`.trim();

      case 'FIELD_GENERATION':
        return activity.status === 'STARTED'
          ? `Creating ${field}`
          : `${field} created${this.elapsedSuffix(activity)}`;

      case 'CHUNK_COMMITTED':
        return `${entity} data batch ${activity.chunk_number ?? ''} saved`.trim();

      case 'PREPARING':
        return activity.status === 'STARTED'
          ? 'Preparing data generation'
          : 'Generation preparation completed';

      case 'COMPLETED':
        return 'Generation completed';

      case 'FAILED':
        return `${entity ? entity + ' ' : ''}generation encountered an issue`;

      default:
        return this.toHumanLabel(activity.stage);
    }
  }

  activityIcon(activity: GenerationActivityEvent): string {
    if (activity.stage === 'SEMANTIC_GENERATION') {
      return 'auto_awesome';
    }

    return this.isActive(activity) ? 'progress_activity' : 'check_circle';
  }

  relativeTime(activity: GenerationActivityEvent): string {
    const timestamp = new Date(activity.timestamp).getTime();

    if (Number.isNaN(timestamp)) {
      return '';
    }

    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));

    if (elapsedSeconds < 10) {
      return 'Just now';
    }

    if (elapsedSeconds < 60) {
      return `${elapsedSeconds}s ago`;
    }

    const minutes = Math.floor(elapsedSeconds / 60);

    if (minutes < 60) {
      return `${minutes} min${minutes === 1 ? '' : 's'} ago`;
    }

    const hours = Math.floor(minutes / 60);

    return `${hours} hr${hours === 1 ? '' : 's'} ago`;
  }

  activityDetail(activity: GenerationActivityEvent): string {
    if (activity.stage === 'SEMANTIC_GENERATION') {
      const progress = this.semanticProgressDetail(activity);

      if (progress) {
        return progress;
      }

      const details: string[] = [];

      if (activity.requested_count != null) {
        details.push(`${activity.requested_count} values`);
      }

      if (activity.status === 'STARTED') {
        details.push('Waiting for AI call details');
      } else if (activity.elapsed_seconds != null) {
        details.push(`${activity.elapsed_seconds.toFixed(1)}s`);
      }

      return details.join(' · ');
    }

    if (activity.stage === 'FIELD_GENERATION') {
      return this.elapsedSuffix(activity).replace(/^ · /, '');
    }

    if (activity.generated_rows != null) {
      return `${activity.generated_rows.toLocaleString()} rows`;
    }

    return '';
  }

  private semanticProgressDetail(
    activity: GenerationActivityEvent,
  ): string | null {
    const call = this.activeSemanticCall();

    if (
      !call ||
      call.entity_name !== activity.entity_name ||
      call.field_name !== activity.field_name
    ) {
      return null;
    }

    const total = `${call.total_unique_count.toLocaleString()}/${call.total_count.toLocaleString()} unique`;

    if (call.status === 'STARTED') {
      return (
        `AI call ${call.attempt_number}/${call.max_attempts} running` +
        ` · ${total} values`
      );
    }

    const details = [
      `Attempt ${call.attempt_number}/${call.max_attempts} completed`,
    ];

    if (call.new_unique_count != null) {
      details.push(`${call.new_unique_count} new`);
    }

    if (call.duplicate_count != null) {
      details.push(`${call.duplicate_count} duplicates`);
    }

    if (call.elapsed_seconds != null) {
      details.push(`${call.elapsed_seconds.toFixed(1)}s`);
    }

    details.push(total);

    return details.join(' · ');
  }

  entityLabel(activity: GenerationActivityEvent): string {
    return this.toHumanLabel(activity.entity_name);
  }

  fieldLabel(activity: GenerationActivityEvent): string {
    return this.toHumanLabel(activity.field_name);
  }

  private semanticMessage(
    activity: GenerationActivityEvent,
    entity: string,
    field: string,
  ): string {
    if (activity.status === 'STARTED') {
      return `FORGE AI is creating ${field}`;
    }

    if (activity.status === 'COMPLETED') {
      return `${field} created`;
    }

    return `${entity} AI generation encountered an issue`;
  }

  private rowsSuffix(activity: GenerationActivityEvent): string {
    if (activity.generated_rows == null) {
      return '';
    }

    return ` · ${activity.generated_rows.toLocaleString()} rows`;
  }

  private elapsedSuffix(activity: GenerationActivityEvent): string {
    if (activity.elapsed_seconds == null) {
      return '';
    }

    return ` · ${activity.elapsed_seconds.toFixed(1)}s`;
  }

  private toHumanLabel(value: string | undefined): string {
    if (!value) {
      return '';
    }

    return value
      .toLowerCase()
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }
}
