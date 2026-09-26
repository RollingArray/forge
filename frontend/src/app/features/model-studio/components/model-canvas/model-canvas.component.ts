import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  input,
  output,
  signal,
} from '@angular/core';

import {
  CanvasEntity,
  ModelRelationship,
} from '../../models/model-studio.models';

import { EntityNodeComponent } from '../entity-node/entity-node.component';

interface CanvasViewport {
  left: number;
  top: number;
  width: number;
  height: number;
}

@Component({
  selector: 'app-model-studio-canvas',
  standalone: true,
  imports: [EntityNodeComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="canvas-shell">

      <div
        #canvasViewport
        class="canvas-viewport"
        (scroll)="handleScroll()"
      >
        <div class="canvas">

          <div class="canvas-grid"></div>

          @for (
            entity of entities();
            track entity.name
          ) {
            <app-model-studio-entity-node
              [entity]="entity"
              [selected]="selectedEntity() === entity.name"
              [style.left.px]="entity.x"
              [style.top.px]="entity.y"
              (selectedChange)="selectEntity($event)"
            />
          }

        </div>
      </div>

    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }

    .canvas-shell {
      position: relative;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
      overflow: hidden;
      background: #f7f8fc;
    }

    .canvas-viewport {
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
      overflow: auto;
      background: #f7f8fc;
      scrollbar-width: thin;
      scrollbar-color: #d4d7e1 transparent;
    }

    .canvas {
      position: relative;
      width: 2100px;
      height: 1250px;
      min-width: 2100px;
      min-height: 1250px;
      background: #f7f8fc;
    }

    .canvas-grid {
      position: absolute;
      inset: 0;
      background-image:
        radial-gradient(
          circle,
          #d8dbe5 0.75px,
          transparent 0.8px
        );
      background-size: 12px 12px;
      pointer-events: none;
    }
  `],
})
export class ModelCanvasComponent
  implements AfterViewInit
{
  @ViewChild('canvasViewport', { static: true })
  private readonly canvasViewport!: ElementRef<HTMLDivElement>;

  readonly entities = input.required<CanvasEntity[]>();
  readonly relationships =
    input.required<ModelRelationship[]>();
  readonly selectedEntity = input('');

  readonly entitySelected = output<string>();

  readonly viewport = signal<CanvasViewport>({
    left: 0,
    top: 0,
    width: 0,
    height: 0,
  });

  ngAfterViewInit(): void {
    this.updateViewport();
  }

  handleScroll(): void {
    this.updateViewport();
  }

  selectEntity(name: string): void {
    this.entitySelected.emit(name);
  }

  private updateViewport(): void {
    const element =
      this.canvasViewport.nativeElement;

    this.viewport.set({
      left: element.scrollLeft,
      top: element.scrollTop,
      width: element.clientWidth,
      height: element.clientHeight,
    });
  }
}
