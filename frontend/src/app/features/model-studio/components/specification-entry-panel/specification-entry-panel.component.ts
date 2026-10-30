import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Output,
} from '@angular/core';

@Component({
  selector: 'app-specification-entry-panel',
  standalone: true,
  templateUrl: './specification-entry-panel.component.html',
  styleUrl: './specification-entry-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpecificationEntryPanelComponent {
  @Output() readonly manualAdd = new EventEmitter<void>();
  @Output() readonly describeWithAi = new EventEmitter<void>();
  @Output() readonly openCsvWizard = new EventEmitter<void>();
}
