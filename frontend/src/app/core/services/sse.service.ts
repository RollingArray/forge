/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: sse.service.ts
 * Purpose: Authenticated Server-Sent Events transport.
 *
 * ============================================================================
 */

import { inject, Injectable } from '@angular/core';
import {
  Observable,
  Subscriber,
} from 'rxjs';

import { AuthService } from './auth.service';

export interface SseEvent {
  type: string;
  data: string;
}

@Injectable({
  providedIn: 'root',
})
export class SseService {
  private readonly authService = inject(AuthService);

  connect(url: string): Observable<SseEvent> {
    return new Observable<SseEvent>((subscriber) => {
      const xhr = new XMLHttpRequest();

      let buffer = '';
      let eventType = 'message';
      let dataLines: string[] = [];
      let processedLength = 0;

      const emitEvent = (): void => {
        if (dataLines.length === 0) {
          eventType = 'message';
          return;
        }

        subscriber.next({
          type: eventType,
          data: dataLines.join('\n'),
        });

        eventType = 'message';
        dataLines = [];
      };

      const processBuffer = (): void => {
        const newContent = xhr.responseText.slice(processedLength);

        if (!newContent) {
          return;
        }

        processedLength = xhr.responseText.length;
        buffer += newContent;

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const rawLine of lines) {
          const line = rawLine.endsWith('\r')
            ? rawLine.slice(0, -1)
            : rawLine;

          if (line === '') {
            emitEvent();
            continue;
          }

          if (line.startsWith(':')) {
            continue;
          }

          const separatorIndex = line.indexOf(':');

          const field = separatorIndex >= 0
            ? line.slice(0, separatorIndex)
            : line;

          let value = separatorIndex >= 0
            ? line.slice(separatorIndex + 1)
            : '';

          if (value.startsWith(' ')) {
            value = value.slice(1);
          }

          switch (field) {
            case 'event':
              eventType = value;
              break;

            case 'data':
              dataLines.push(value);
              break;

            default:
              break;
          }
        }
      };

      xhr.onprogress = () => {
        processBuffer();
      };

      xhr.onload = () => {
        processBuffer();
        emitEvent();

        if (xhr.status >= 200 && xhr.status < 300) {
          subscriber.complete();
          return;
        }

        subscriber.error(
          new Error(
            `SSE request failed with HTTP status ${xhr.status}.`,
          ),
        );
      };

      xhr.onerror = () => {
        subscriber.error(
          new Error('SSE connection failed.'),
        );
      };

      xhr.onabort = () => {
        if (!subscriber.closed) {
          subscriber.complete();
        }
      };

      const session = this.authService.getSession();

      xhr.open('GET', url, true);
      xhr.setRequestHeader('Accept', 'text/event-stream');
      xhr.setRequestHeader('Cache-Control', 'no-cache');

      if (session?.accessToken) {
        xhr.setRequestHeader(
          'Authorization',
          `${session.tokenType} ${session.accessToken}`,
        );
      }

      xhr.send();

      return () => {
        xhr.abort();
      };
    });
  }
}
