import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-favorites-collection-toolbar',
  standalone: true,
  imports: [WorkspaceHeaderComponent],
  templateUrl: './favorites-collection-toolbar.component.html',
  styleUrl: './favorites-collection-toolbar.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoritesCollectionToolbarComponent {
  readonly totalCount = input.required<number>();
  readonly query = input('');
  readonly queryChange = output<string>();
}
