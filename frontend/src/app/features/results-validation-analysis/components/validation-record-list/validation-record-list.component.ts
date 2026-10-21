import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { ValidationRecord } from '../../../../core/interfaces/validation-record.interface';
import { ValidationRecordCardComponent } from '../validation-record-card/validation-record-card.component';

@Component({
  selector: 'app-validation-record-list',
  standalone: true,
  imports: [ValidationRecordCardComponent],
  templateUrl: './validation-record-list.component.html',
  styleUrl: './validation-record-list.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ValidationRecordListComponent {
  readonly records = input.required<readonly ValidationRecord[]>();
}
