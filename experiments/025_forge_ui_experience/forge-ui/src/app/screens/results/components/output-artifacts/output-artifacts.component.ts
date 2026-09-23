import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { ResultsArtifact } from '../../models/results.models';

@Component({
  selector: 'app-output-artifacts',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './output-artifacts.component.html',
  styleUrl: './output-artifacts.component.css',
})
export class OutputArtifactsComponent {
  readonly artifacts =
    input.required<readonly ResultsArtifact[]>();

  readonly downloadRequested =
    output<ResultsArtifact>();

  requestDownload(
    artifact: ResultsArtifact,
  ): void {
    this.downloadRequested.emit(
      artifact,
    );
  }
}
