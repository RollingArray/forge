import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Template } from '../../models/home.models';

@Component({
  selector: 'app-template-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './template-card.component.html',
  styleUrl: './template-card.component.css',
})
export class TemplateCardComponent {
  readonly template = input.required<Template>();

  readonly use = output<string>();

  useTemplate(): void {
    this.use.emit(this.template().name);
  }
}
