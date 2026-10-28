import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { AiAssistPanelComponent } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';
import { DescriptionLearningPanelComponent } from '../description-learning-panel/description-learning-panel.component';

@Component({
  selector: 'app-authoring-input',
  standalone: true,
  imports: [AiAssistPanelComponent, DescriptionLearningPanelComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './authoring-input.component.html',
  styleUrl: './authoring-input.component.css',
})
export class AuthoringInputComponent {
  @Input() prompt = '';
  @Input() generating = false;
  @Input() hasProposal = false;
  @Input() errorMessage: string | null = null;
  @Input() showGuide = false;

  @Output() promptChange = new EventEmitter<string>();
  @Output() generate = new EventEmitter<string>();
  @Output() clear = new EventEmitter<void>();
  @Output() guideToggle = new EventEmitter<void>();
  @Output() exampleSelected = new EventEmitter<void>();
}
