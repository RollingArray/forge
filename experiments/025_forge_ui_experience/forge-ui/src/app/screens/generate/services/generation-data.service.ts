import { Injectable } from '@angular/core';

import {
  GenerationArtifacts,
  GenerationCheckpoint,
  GenerationQuality,
  GenerationValidation,
} from '../models/generate.models';

@Injectable({
  providedIn: 'root',
})
export class GenerationDataService {
  private readonly endpoints = {
    checkpoint: '/forge-data/generation/checkpoint.json',
    quality: '/forge-data/generation/quality.json',
    validation: '/forge-data/generation/validation.json',
  } as const;

  async load(): Promise<GenerationArtifacts> {
    const [
      checkpoint,
      quality,
      validation,
    ] = await Promise.all([
      this.loadJson<GenerationCheckpoint>(
        this.endpoints.checkpoint,
      ),
      this.loadJson<{
        job_id: string;
        specification: string;
        dataset: string;
        quality: GenerationQuality;
      }>(this.endpoints.quality),
      this.loadJson<GenerationValidation>(
        this.endpoints.validation,
      ),
    ]);

    return {
      checkpoint,
      quality: quality.quality,
      validation,
    };
  }

  private async loadJson<T>(url: string): Promise<T> {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(
        `Unable to load generation artifact: ${url} (${response.status})`,
      );
    }

    return (await response.json()) as T;
  }
}
