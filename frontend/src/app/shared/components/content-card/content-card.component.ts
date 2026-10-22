import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

@Component({
  selector: 'app-content-card',
  standalone: true,
  templateUrl: './content-card.component.html',
  styleUrl: './content-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContentCardComponent {
  readonly padding = input<string | number | null>(null);
}
