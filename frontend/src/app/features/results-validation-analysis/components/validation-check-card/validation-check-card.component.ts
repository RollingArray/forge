import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { ValidationCheck } from '../../../../core/interfaces/validation-check.interface';
import { ValidationRecordListComponent } from '../validation-record-list/validation-record-list.component';

@Component({
  selector: 'app-validation-check-card',
  standalone: true,
  imports: [ValidationRecordListComponent],
  templateUrl: './validation-check-card.component.html',
  styleUrl: './validation-check-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ValidationCheckCardComponent {
  readonly check = input.required<ValidationCheck>();
}
