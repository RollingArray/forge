import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Template } from '../../models/home.models';
import { TemplateCardComponent } from '../template-card/template-card.component';

@Component({
  selector: 'app-home-templates',
  standalone: true,
  imports: [TemplateCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './templates.component.html',
  styleUrl: './templates.component.css',
})
export class TemplatesComponent {
  readonly templates = input.required<Template[]>();

  readonly templateSelected = output<string>();
  readonly viewAll = output<void>();

  useTemplate(name: string): void {
    this.templateSelected.emit(name);
  }

  showAll(): void {
    this.viewAll.emit();
  }
}
