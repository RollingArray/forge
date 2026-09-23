import { Injectable } from '@angular/core';

import {
  ResultsCheckpoint,
  ResultsQuality,
  ResultsValidation,
} from '../models/results.models';

interface ResultsQualityDocument {
  dataset: string;
  job_id: string;
  quality: ResultsQuality;
  specification: string;
}

@Injectable({
  providedIn: 'root',
})
export class ResultsDataService {
  private readonly checkpointUrl =
    '/forge-data/generation/checkpoint.json';

  private readonly qualityUrl =
    '/forge-data/generation/quality.json';

  private readonly validationUrl =
    '/forge-data/generation/validation.json';

  async loadPromise(): Promise<{
    checkpoint: ResultsCheckpoint;
    quality: ResultsQuality;
    validation: ResultsValidation;
  }> {
    const [
      checkpoint,
      qualityDocument,
      validation,
    ] = await Promise.all([
      this.loadJson<ResultsCheckpoint>(
        this.checkpointUrl,
      ),
      this.loadJson<ResultsQualityDocument>(
        this.qualityUrl,
      ),
      this.loadJson<ResultsValidation>(
        this.validationUrl,
      ),
    ]);

    return {
      checkpoint,
      quality: qualityDocument.quality,
      validation,
    };
  }

  private async loadJson<T>(
    url: string,
  ): Promise<T> {
    const response =
      await fetch(url);

    if (!response.ok) {
      throw new Error(
        `Unable to load ${url}: ${response.status}`,
      );
    }

    return response.json() as Promise<T>;
  }
}
