/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: notification.service.ts
 * Purpose: Provides application-wide notification state and presentation
 *          behavior for FORGE.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { Injectable, signal } from '@angular/core';

export type NotificationType =
  | 'SUCCESS'
  | 'INFO'
  | 'WARNING'
  | 'ERROR';

export interface Notification {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  duration: number;
  status?: number | null;
}

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private readonly notificationsState = signal<Notification[]>([]);

  readonly notifications = this.notificationsState.asReadonly();

  private nextId = 0;

  success(
    title: string,
    message: string,
    duration = 3000,
  ): void {
    this.show({
      type: 'SUCCESS',
      title,
      message,
      duration,
    });
  }

  info(
    title: string,
    message: string,
    duration = 4000,
  ): void {
    this.show({
      type: 'INFO',
      title,
      message,
      duration,
    });
  }

  warning(
    title: string,
    message: string,
    duration = 5000,
  ): void {
    this.show({
      type: 'WARNING',
      title,
      message,
      duration,
    });
  }

  error(
    title: string,
    message: string,
    status: number | null = null,
    duration = 6000,
  ): void {
    this.show({
      type: 'ERROR',
      title,
      message,
      status,
      duration,
    });
  }

  dismiss(id: number): void {
    this.notificationsState.update((notifications) =>
      notifications.filter((notification) => notification.id !== id),
    );
  }

  private show(
    notification: Omit<Notification, 'id'>,
  ): void {
    const id = ++this.nextId;

    this.notificationsState.update((notifications) => [
      ...notifications,
      {
        ...notification,
        id,
      },
    ]);

    window.setTimeout(() => {
      this.dismiss(id);
    }, notification.duration);
  }
}
