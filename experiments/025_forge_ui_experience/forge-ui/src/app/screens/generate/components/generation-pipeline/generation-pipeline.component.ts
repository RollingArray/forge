import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { GenerationPipelineStage } from '../../models/generate.models';

@Component({
  selector: 'app-generation-pipeline',
  standalone: true,
  templateUrl: './generation-pipeline.component.html',
  styleUrl: './generation-pipeline.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationPipelineComponent {
  readonly stages =
    input.required<readonly GenerationPipelineStage[]>();
}
