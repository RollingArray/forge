import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { environment } from '../../../../environments/environment';
import { ApiLoadingMessage } from '../../../core/enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../../../core/tokens/api-loading-message.token';
import { SseService } from '../../../core/services/sse.service';
import { GenerationService } from './generation.service';

describe('GenerationService dedicated Results APIs', () => {
  let service: GenerationService;
  let http: HttpTestingController;

  const dataModelId = 'd7bc59b7-82e2-455c-a884-65eac8bf106f';
  const jobId = '8B86940D2C4D408384F48339EB9134E2';

  const baseUrl =
    `${environment.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: SseService,
          useValue: { connect: vi.fn() },
        },
      ],
    });

    service = TestBed.inject(GenerationService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('requests the dedicated Execution endpoint and preserves its response', () => {
    const payload = {
      data_model_id: dataModelId,
      job_id: jobId,
      status: 'COMPLETED',
      error: null,
      created_at: '2026-11-13T16:18:13.756943Z',
      started_at: '2026-11-13T16:18:13.767004Z',
      completed_at: '2026-11-13T16:32:11.336707Z',
      total_target_rows: 7000,
      total_generated_rows: 7000,
      progress: 1,
      elapsed_seconds: 836.851139,
      peak_memory_mb: 130.875,
      throughput_rows_per_second: 8.364689,
      entities: [
        {
          entity_name: 'CUSTOMER',
          target_rows: 823,
          generated_rows: 823,
          completed_chunks: 17,
          total_chunks: 17,
          status: 'COMPLETED',
          elapsed_seconds: 42.614267,
          throughput_rows_per_second: 19.31278,
          peak_memory_mb: 111.875,
        },
      ],
    };

    let actual: unknown;

    service.getGenerationExecution(dataModelId, jobId).subscribe({
      next: (response) => {
        actual = response;
      },
    });

    const request = http.expectOne(`${baseUrl}/execution`);

    expect(request.request.method).toBe('GET');
    expect(
      request.request.context.get(API_LOADING_MESSAGE),
    ).toBe(ApiLoadingMessage.LoadingGenerationExecution);

    request.flush(payload);

    expect(actual).toEqual(payload);
  });

  it('requests the dedicated Validation endpoint and preserves its evidence', () => {
    const payload = {
      data_model_id: dataModelId,
      job_id: jobId,
      validation: {
        valid: true,
        entity_count: 17,
        expected_rows: 7000,
        generated_rows: 7000,
        error_count: 0,
        errors: [],
        warnings: [],
        evidence: {
          foreign_keys: {
            relationships_checked: 19,
          },
          constraints: {
            constraints_checked: 12,
          },
        },
      },
    };

    let actual: unknown;

    service.getGenerationValidation(dataModelId, jobId).subscribe({
      next: (response) => {
        actual = response;
      },
    });

    const request = http.expectOne(`${baseUrl}/validation`);

    expect(request.request.method).toBe('GET');
    expect(
      request.request.context.get(API_LOADING_MESSAGE),
    ).toBe(ApiLoadingMessage.LoadingGenerationValidation);

    request.flush(payload);

    expect(actual).toEqual(payload);
  });

  it('propagates Execution HTTP errors to the caller', () => {
    let actualError: unknown;

    service.getGenerationExecution(dataModelId, jobId).subscribe({
      error: (error) => {
        actualError = error;
      },
    });

    const request = http.expectOne(`${baseUrl}/execution`);

    request.flush(
      { detail: 'Execution unavailable' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    expect(actualError).toBeTruthy();
    expect((actualError as { status: number }).status).toBe(500);
  });

  it('propagates Validation HTTP errors to the caller', () => {
    let actualError: unknown;

    service.getGenerationValidation(dataModelId, jobId).subscribe({
      error: (error) => {
        actualError = error;
      },
    });

    const request = http.expectOne(`${baseUrl}/validation`);

    request.flush(
      { detail: 'Validation unavailable' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    expect(actualError).toBeTruthy();
    expect((actualError as { status: number }).status).toBe(500);
  });
});
