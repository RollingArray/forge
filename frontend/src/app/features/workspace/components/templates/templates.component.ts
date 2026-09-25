/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: templates.component.ts
 * Purpose: Defines the templates Workspace component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Template } from '../../../../core/interfaces/template.interface';
import { TemplateCardComponent } from '../template-card/template-card.component';

@Component({
  selector: 'app-workspace-templates',
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
