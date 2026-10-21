import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { ValidationRecord } from '../../../../core/interfaces/validation-record.interface';

@Component({
  selector: 'app-validation-record-card',
  standalone: true,
  templateUrl: './validation-record-card.component.html',
  styleUrl: './validation-record-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ValidationRecordCardComponent {
  readonly record = input.required<ValidationRecord>();
}
