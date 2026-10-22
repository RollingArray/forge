import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { DatePipe, UpperCasePipe } from '@angular/common';
import { ContentCardComponent } from '../../../../shared/components/content-card/content-card.component';
import { ForgeButtonComponent } from '../../../../shared/components/forge-button/forge-button.component';

import { Favorite } from '../../../../core/interfaces/favorite.interface';
import { ResourceDefinition } from '../../../../core/interfaces/resource-definition.interface';

@Component({
  selector: 'app-favorite-card',
  standalone: true,
  imports: [DatePipe, UpperCasePipe, ContentCardComponent, ForgeButtonComponent],
  templateUrl: './favorite-card.component.html',
  styleUrl: './favorite-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoriteCardComponent {
  readonly favorite = input.required<Favorite>();
  readonly definition = input.required<ResourceDefinition>();
  readonly categoryId = input.required<string>();
  readonly removing = input(false);
  readonly busy = input(false);

  readonly open = output<Favorite>();
  readonly remove = output<Favorite>();
}
