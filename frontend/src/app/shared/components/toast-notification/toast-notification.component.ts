/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: toast-notification.component.ts
 * Purpose: Global presentation of FORGE application notifications.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  inject,
} from '@angular/core';

import {
  NotificationService,
} from '../../../core/services/notification.service';

@Component({
  selector: 'app-toast-notification',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './toast-notification.component.html',
  styleUrl: './toast-notification.component.css',
})
export class ToastNotificationComponent {
  readonly notificationService = inject(NotificationService);

  dismiss(id: number): void {
    this.notificationService.dismiss(id);
  }
}
