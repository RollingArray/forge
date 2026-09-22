import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  input,
  output,
  signal,
  ViewChild,
} from '@angular/core';

import {
  CanvasEntity,
  ModelRelationship,
} from '../../models/model-studio.models';

import { EntityNodeComponent } from '../entity-node/entity-node.component';
import { RelationshipLayerComponent } from '../relationship-layer/relationship-layer.component';
import { ModelMinimapComponent } from '../model-minimap/model-minimap.component';

interface CanvasViewport {
  left: number;
  top: number;
  width: number;
  height: number;
}

@Component({
  selector: 'app-model-canvas',
  standalone: true,
  imports: [
    EntityNodeComponent,
    RelationshipLayerComponent,
    ModelMinimapComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './model-canvas.component.html',
  styleUrl: './model-canvas.component.css',
})
export class ModelCanvasComponent implements AfterViewInit {
  @ViewChild('canvasViewport', { static: true })
  private readonly canvasViewport!: ElementRef<HTMLDivElement>;

  readonly entities = input.required<CanvasEntity[]>();
  readonly relationships = input.required<ModelRelationship[]>();
  readonly selectedEntity = input<string>('');

  readonly entitySelected = output<string>();

  readonly viewport = signal<CanvasViewport>({
    left: 0,
    top: 0,
    width: 0,
    height: 0,
  });

  private readonly canvasWidth = 2100;
  private readonly canvasHeight = 1250;

  ngAfterViewInit(): void {
    this.updateViewport();
  }

  handleScroll(): void {
    this.updateViewport();
  }

  private updateViewport(): void {
    const element = this.canvasViewport.nativeElement;

    this.viewport.set({
      left: element.scrollLeft,
      top: element.scrollTop,
      width: element.clientWidth,
      height: element.clientHeight,
    });
  }

  selectEntity(name: string): void {
    this.entitySelected.emit(name);
  }

  get canvasSize(): { width: number; height: number } {
    return {
      width: this.canvasWidth,
      height: this.canvasHeight,
    };
  }
}
