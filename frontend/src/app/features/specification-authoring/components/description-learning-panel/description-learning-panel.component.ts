import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';

@Component({
  selector: 'app-description-learning-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './description-learning-panel.component.html',
  styleUrl: './description-learning-panel.component.css',
})
export class DescriptionLearningPanelComponent {
  @Input() showGuide = false;
  @Input() generating = false;

  @Output() guideToggle = new EventEmitter<void>();
  @Output() exampleSelected = new EventEmitter<void>();
}
