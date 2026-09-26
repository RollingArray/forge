import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

@Component({
  selector: 'app-field-parameter-header',
  standalone: true,
  templateUrl: './field-parameter-header.component.html',
  styleUrl: './field-parameter-header.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FieldParameterHeaderComponent {
  readonly title = input.required<string>();
  readonly description = input.required<string>();
}
