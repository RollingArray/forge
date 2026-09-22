import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { CanvasEntity, EntityAccent, ModelRelationship } from '../../models/model-studio.models';

interface Point {
  x: number;
  y: number;
}

type ConnectionSide = 'top' | 'right' | 'bottom' | 'left';

interface ConnectionPoint extends Point {
  side: ConnectionSide;
}

interface RelationshipLayout {
  relationship: ModelRelationship;
  index: number;
  source: CanvasEntity;
  target: CanvasEntity;
  sourceSide: ConnectionSide;
  targetSide: ConnectionSide;
  sourcePort: ConnectionPoint;
  targetPort: ConnectionPoint;
}

interface RelationshipPath {
  key: string;
  path: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  labelX: number;
  labelY: number;
  cardinality: string;
  gradientId: string;
  sourceColor: string;
  targetColor: string;
}

interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

interface SearchState {
  node: number;
  direction: 0 | 1 | 2;
  g: number;
  f: number;
  parent: number;
  parentDirection: 0 | 1 | 2;
}

interface HeapItem {
  state: number;
  priority: number;
}

const ENTITY_COLORS: Record<EntityAccent, string> = {
  blue: '#4f6df5',
  green: '#25a56a',
  orange: '#e79520',
  pink: '#e85b9f',
  purple: '#8b6bd9',
  teal: '#159f9a',
  amber: '#d49a18',
  cyan: '#269bc5',
  indigo: '#5b5fc7',
  rose: '#d95772',
};

@Component({
  selector: 'app-relationship-layer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './relationship-layer.component.html',
  styleUrl: './relationship-layer.component.css',
})
export class RelationshipLayerComponent {
  readonly entities = input.required<CanvasEntity[]>();
  readonly relationships = input.required<ModelRelationship[]>();

  /*
   * Must match the SVG dimensions already used by the
   * relationship-layer template.
   */
  private readonly canvasWidth = 2100;
  private readonly canvasHeight = 1250;

  /*
   * Physical port layout.
   */
  private readonly portSpacing = 72;
  private readonly portInset = 24;

  /*
   * Distance from the entity boundary to the routing area.
   */
  private readonly routeOffset = 28;

  /*
   * Clearance around entity cards.
   */
  private readonly obstacleClearance = 14;

  /*
   * Keep relationship routing away from the outer
   * canvas boundary so the graph has balanced breathing
   * room on all four sides.
   */
  private readonly canvasMargin = 60;

  /*
   * Clearance around already-used relationship routes.
   */
  private readonly routeClearance = 12;

  /*
   * Larger than the old value because route movement now
   * uses actual physical distance.
   */
  private readonly bendPenalty = 140;

  private readonly cornerRadius = 12;

  /*
   * Cardinality label distance from the source endpoint.
   */
  private readonly labelDistance = 52;

  readonly paths = computed<RelationshipPath[]>(() => {
    const entities = this.entities();
    const relationships = this.relationships();

    const sideLayouts =
      this.assignConnectionSides(
        entities,
        relationships,
      );

    const layouts =
      this.allocatePorts(
        sideLayouts,
      );

    const routingOrder =
      [...layouts].sort(
        (a, b) =>
          this.relationshipRoutingPriority(b) -
            this.relationshipRoutingPriority(a) ||
          a.index - b.index,
      );

    const reservedRoutes: Rect[] = [];
    const routed = new Map<number, RelationshipPath>();

    /*
     * Temporary diagnostic information.
     *
     * This is intentionally kept separate from the
     * rendered RelationshipPath model.
     */
    const diagnostics: Array<{
      relationship: string;
      sourceDot: string;
      targetDot: string;
      sourceSide: string;
      targetSide: string;
      segments: number;
      routeLength: number;
      status: string;
    }> = [];

    for (const layout of routingOrder) {
      const routePoints =
        this.buildRoutePoints(
          layout,
          reservedRoutes,
        );

      const path =
        this.roundedPolyline(
          routePoints,
          this.cornerRadius,
        );

      const labelPoint =
        this.findLabelPoint(
          routePoints,
        );

      const relationshipPath: RelationshipPath = {
        key:
          `${layout.relationship.source}-${layout.relationship.target}-${layout.index}`,

        path,

        sourceX:
          layout.sourcePort.x,

        sourceY:
          layout.sourcePort.y,

        targetX:
          layout.targetPort.x,

        targetY:
          layout.targetPort.y,

        labelX:
          labelPoint.x,

        labelY:
          labelPoint.y,

        cardinality:
          this.cardinalityForRelationship(
            layout.relationship,
          ),

        gradientId:
          `relationship-gradient-${layout.index}`,

        sourceColor:
          ENTITY_COLORS[
            layout.source.accent
          ],

        targetColor:
          ENTITY_COLORS[
            layout.target.accent
          ],
      };

      routed.set(
        layout.index,
        relationshipPath,
      );

      const routeLength =
        this.routeLength(
          routePoints,
        );

      const segments =
        Math.max(
          0,
          routePoints.length - 1,
        );

      const sourceConnected =
        routePoints.length >= 2 &&
        this.samePoint(
          routePoints[0],
          {
            x: layout.sourcePort.x,
            y: layout.sourcePort.y,
          },
        ) &&
        routeLength > 0;

      const targetConnected =
        routePoints.length >= 2 &&
        this.samePoint(
          routePoints[
            routePoints.length - 1
          ],
          {
            x: layout.targetPort.x,
            y: layout.targetPort.y,
          },
        ) &&
        routeLength > 0;

      let status = 'OK';

      if (routePoints.length < 2) {
        status = 'NO_ROUTE';
      } else if (routeLength <= 0) {
        status = 'ZERO_LENGTH';
      } else if (!sourceConnected) {
        status = 'SOURCE_NOT_CONNECTED';
      } else if (!targetConnected) {
        status = 'TARGET_NOT_CONNECTED';
      }

      diagnostics.push({
        relationship:
          `${layout.relationship.source} → ${layout.relationship.target}`,

        sourceDot:
          `(${Math.round(layout.sourcePort.x)}, ${Math.round(layout.sourcePort.y)})`,

        targetDot:
          `(${Math.round(layout.targetPort.x)}, ${Math.round(layout.targetPort.y)})`,

        sourceSide:
          layout.sourceSide,

        targetSide:
          layout.targetSide,

        segments,

        routeLength:
          Math.round(routeLength),

        status,
      });

      reservedRoutes.push(
        ...this.buildRouteReservations(
          routePoints,
        ),
      );
    }

    /*
     * Print the complete diagnostic table.
     *
     * The table is sorted back into specification order
     * so it is easy to compare with specification.json.
     */
    const orderedDiagnostics =
      [...diagnostics].sort(
        (a, b) =>
          relationships.findIndex(
            relationship =>
              `${relationship.source} → ${relationship.target}` ===
              a.relationship,
          ) -
          relationships.findIndex(
            relationship =>
              `${relationship.source} → ${relationship.target}` ===
              b.relationship,
          ),
      );

    console.groupCollapsed(
      '[FORGE] Relationship routing diagnostics',
    );

    console.table(
      orderedDiagnostics,
    );

    const problems =
      orderedDiagnostics.filter(
        item =>
          item.status !== 'OK',
      );

    if (problems.length > 0) {
      console.warn(
        `[FORGE] ${problems.length} relationship route(s) have geometry problems.`,
      );

      console.table(
        problems,
      );
    } else {
      console.info(
        `[FORGE] All ${orderedDiagnostics.length} relationship routes have valid endpoint geometry.`,
      );
    }

    console.groupEnd();

    return layouts
      .sort(
        (a, b) =>
          a.index - b.index,
      )
      .map(layout =>
        routed.get(
          layout.index,
        ),
      )
      .filter(
        (
          path,
        ): path is RelationshipPath =>
          !!path,
      );
  });


  private relationshipRoutingPriority(layout: RelationshipLayout): number {
    const sourceCenter = this.entityCenter(layout.source);

    const targetCenter = this.entityCenter(layout.target);

    return this.manhattan(sourceCenter, targetCenter);
  }

  private assignConnectionSides(
    entities: CanvasEntity[],
    relationships: ModelRelationship[],
  ): Omit<RelationshipLayout, 'sourcePort' | 'targetPort'>[] {
    const layouts: Omit<RelationshipLayout, 'sourcePort' | 'targetPort'>[] = [];

    const usage = new Map<string, Map<ConnectionSide, number>>();

    const getUsage = (entityName: string): Map<ConnectionSide, number> => {
      let entityUsage = usage.get(entityName);

      if (!entityUsage) {
        entityUsage = new Map([
          ['top', 0],
          ['right', 0],
          ['bottom', 0],
          ['left', 0],
        ]);

        usage.set(entityName, entityUsage);
      }

      return entityUsage;
    };

    for (let index = 0; index < relationships.length; index++) {
      const relationship = relationships[index];

      const source = entities.find((entity) => entity.name === relationship.source);

      const target = entities.find((entity) => entity.name === relationship.target);

      if (!source || !target) {
        continue;
      }

      const sourceUsage = getUsage(source.name);

      const targetUsage = getUsage(target.name);

      const sourcePreferred = this.connectionSide(source, target);

      const targetPreferred = this.connectionSide(target, source);

      const sourceSide =
        this.selectAvailableSide(
          source,
          sourcePreferred,
          sourceUsage,
        );

      const targetSide =
        this.selectAvailableSide(
          target,
          targetPreferred,
          targetUsage,
        );

      sourceUsage.set(sourceSide, (sourceUsage.get(sourceSide) ?? 0) + 1);

      targetUsage.set(targetSide, (targetUsage.get(targetSide) ?? 0) + 1);

      layouts.push({
        relationship,
        index,
        source,
        target,
        sourceSide,
        targetSide,
      });
    }

    return layouts;
  }

  private selectAvailableSide(
    entity: CanvasEntity,
    preferred: ConnectionSide,
    usage: Map<ConnectionSide, number>,
  ): ConnectionSide {
    const sides: ConnectionSide[] = ['top', 'right', 'bottom', 'left'];

    let bestSide = preferred;
    let bestScore = Number.POSITIVE_INFINITY;

    for (const side of sides) {
      const used = usage.get(side) ?? 0;

      const capacity = this.sideCapacity(entity, side);

      const overflowPenalty = used >= capacity ? 100000 : 0;

      const directionalPenalty = this.sideDirectionPenalty(preferred, side);

      /*
       * Direction remains the dominant factor.
       * Usage spreads connections only when it is
       * reasonably close to the preferred direction.
       */
      const score = overflowPenalty + directionalPenalty * 1000 + used * 180;

      if (score < bestScore) {
        bestScore = score;
        bestSide = side;
      }
    }

    return bestSide;
  }

  private sideDirectionPenalty(preferred: ConnectionSide, candidate: ConnectionSide): number {
    if (preferred === candidate) {
      return 0;
    }

    const opposite =
      (preferred === 'top' && candidate === 'bottom') ||
      (preferred === 'bottom' && candidate === 'top') ||
      (preferred === 'left' && candidate === 'right') ||
      (preferred === 'right' && candidate === 'left');

    return opposite ? 2 : 1;
  }

  private sideCapacity(entity: CanvasEntity, side: ConnectionSide): number {
    const sideLength = side === 'top' || side === 'bottom' ? entity.width : entity.height;

    const usableLength = Math.max(0, sideLength - this.portInset * 2);

    return Math.max(1, Math.floor(usableLength / this.portSpacing) + 1);
  }

  private allocatePorts(
    layouts: Omit<RelationshipLayout, 'sourcePort' | 'targetPort'>[],
  ): RelationshipLayout[] {
    const result: RelationshipLayout[] = layouts.map((layout) => ({
      ...layout,
      sourcePort: {
        x: 0,
        y: 0,
        side: layout.sourceSide,
      },
      targetPort: {
        x: 0,
        y: 0,
        side: layout.targetSide,
      },
    }));

    this.allocateEndpointPorts(result, 'source');

    this.allocateEndpointPorts(result, 'target');

    return result;
  }

  private allocateEndpointPorts(
    layouts: RelationshipLayout[],
    endpoint: 'source' | 'target',
  ): void {
    const groups = new Map<string, RelationshipLayout[]>();

    for (const layout of layouts) {
      const entity = endpoint === 'source' ? layout.source : layout.target;

      const side = endpoint === 'source' ? layout.sourceSide : layout.targetSide;

      const key = `${entity.name}:${side}`;

      const group = groups.get(key) ?? [];

      group.push(layout);
      groups.set(key, group);
    }

    for (const group of groups.values()) {
      group.sort((a, b) => a.index - b.index);

      const count = group.length;

      for (let slot = 0; slot < count; slot++) {
        const layout = group[slot];

        const entity = endpoint === 'source' ? layout.source : layout.target;

        const side = endpoint === 'source' ? layout.sourceSide : layout.targetSide;

        const point = this.connectionPoint(entity, side, slot, count);

        if (endpoint === 'source') {
          layout.sourcePort = point;
        } else {
          layout.targetPort = point;
        }
      }
    }
  }

  private connectionPoint(
    entity: CanvasEntity,
    side: ConnectionSide,
    slot: number,
    count: number,
  ): ConnectionPoint {
    const centerX = entity.x + entity.width / 2;

    const centerY = entity.y + entity.height / 2;

    const sideLength = side === 'top' || side === 'bottom' ? entity.width : entity.height;

    const usableLength = Math.max(0, sideLength - this.portInset * 2);

    const spacing = count <= 1 ? 0 : Math.min(this.portSpacing, usableLength / (count - 1));

    const totalSpan = spacing * (count - 1);

    const offset = slot * spacing - totalSpan / 2;

    switch (side) {
      case 'top':
        return {
          x: centerX + offset,
          y: entity.y,
          side,
        };

      case 'right':
        return {
          x: entity.x + entity.width,
          y: centerY + offset,
          side,
        };

      case 'bottom':
        return {
          x: centerX + offset,
          y: entity.y + entity.height,
          side,
        };

      case 'left':
        return {
          x: entity.x,
          y: centerY + offset,
          side,
        };
    }
  }

  private buildRoutePoints(
    layout: RelationshipLayout,
    reservedRoutes: Rect[],
  ): Point[] {
    const source = layout.sourcePort;

    const target = layout.targetPort;

    const sourceExit =
      this.offsetPoint(
        source,
        this.routeOffset,
      );

    const targetExit =
      this.offsetPoint(
        target,
        this.routeOffset,
      );

    const entityObstacles =
      this.buildEntityObstacles(
        this.entities(),
      );

    /*
     * Existing relationship corridors are additional
     * obstacles. This is what prevents multiple
     * relationships from collapsing onto the same route.
     */
    const obstacles = [
      ...entityObstacles,
      ...reservedRoutes,
    ];

    const routed =
      this.findOrthogonalRoute(
        sourceExit,
        targetExit,
        obstacles,
      );

    return this.removeDuplicatePoints([
      {
        x: source.x,
        y: source.y,
      },
      sourceExit,
      ...routed.slice(1, -1),
      targetExit,
      {
        x: target.x,
        y: target.y,
      },
    ]);
  }

  private buildEntityObstacles(entities: CanvasEntity[]): Rect[] {
    return entities.map((entity) => ({
      left: Math.max(0, entity.x - this.obstacleClearance),

      top: Math.max(0, entity.y - this.obstacleClearance),

      right: Math.min(this.canvasWidth, entity.x + entity.width + this.obstacleClearance),

      bottom: Math.min(this.canvasHeight, entity.y + entity.height + this.obstacleClearance),
    }));
  }

  /**
   * Turn an already-used route into thin rectangular
   * corridors that subsequent routes must avoid.
   *
   * Endpoint stubs are deliberately excluded. That allows
   * multiple relationships to leave the same entity through
   * separate ports without blocking each other.
   */
  private buildRouteReservations(points: Point[]): Rect[] {
    if (points.length < 4) {
      return [];
    }

    const reservations: Rect[] = [];

    /*
     * Ignore:
     *
     * points[0] -> points[1]
     *
     * and
     *
     * points[last-1] -> points[last]
     *
     * because those are the short endpoint stubs.
     */
    for (let index = 1; index < points.length - 2; index++) {
      const start = points[index];

      const end = points[index + 1];

      if (Math.abs(start.x - end.x) < 0.001) {
        const top = Math.min(start.y, end.y);

        const bottom = Math.max(start.y, end.y);

        reservations.push({
          left: Math.max(0, start.x - this.routeClearance),

          right: Math.min(this.canvasWidth, start.x + this.routeClearance),

          top,
          bottom,
        });
      } else if (Math.abs(start.y - end.y) < 0.001) {
        const left = Math.min(start.x, end.x);

        const right = Math.max(start.x, end.x);

        reservations.push({
          left,
          right,

          top: Math.max(0, start.y - this.routeClearance),

          bottom: Math.min(this.canvasHeight, start.y + this.routeClearance),
        });
      }
    }

    return reservations;
  }

  private findOrthogonalRoute(start: Point, goal: Point, obstacles: Rect[]): Point[] {
    if (this.samePoint(start, goal)) {
      return [start, goal];
    }

    const xValues = this.routeCoordinates(obstacles, 'x', start, goal);

    const yValues = this.routeCoordinates(obstacles, 'y', start, goal);

    const xCount = xValues.length;

    const yCount = yValues.length;

    const nodeCount = xCount * yCount;

    const startNode = this.nodeIndex(
      this.coordinateIndex(xValues, start.x),
      this.coordinateIndex(yValues, start.y),
      xCount,
    );

    const goalNode = this.nodeIndex(
      this.coordinateIndex(xValues, goal.x),
      this.coordinateIndex(yValues, goal.y),
      xCount,
    );

    const stateCount = nodeCount * 3;

    const gScore = new Array<number>(stateCount).fill(Number.POSITIVE_INFINITY);

    const parent = new Array<number>(stateCount).fill(-1);

    const parentDirection = new Array<0 | 1 | 2>(stateCount).fill(0);

    const open = new MinHeap();

    /*
     * Direction 0 means "no previous direction".
     * Direction 1 = horizontal.
     * Direction 2 = vertical.
     */
    const startState = this.stateIndex(startNode, 0);

    gScore[startState] = 0;

    open.push({
      state: startState,
      priority: this.manhattan(start, goal),
    });

    let goalState = -1;

    while (!open.isEmpty()) {
      const current = open.pop();

      if (!current) {
        break;
      }

      const currentState = current.state;

      const currentNode = Math.floor(currentState / 3);

      const currentDirection = (currentState % 3) as 0 | 1 | 2;

      if (currentNode === goalNode) {
        goalState = currentState;
        break;
      }

      const currentXIndex = currentNode % xCount;

      const currentYIndex = Math.floor(currentNode / xCount);

      const currentPoint: Point = {
        x: xValues[currentXIndex],

        y: yValues[currentYIndex],
      };

      /*
       * Horizontal neighbors.
       */
      for (const deltaX of [-1, 1]) {
        const nextXIndex = currentXIndex + deltaX;

        if (nextXIndex < 0 || nextXIndex >= xCount) {
          continue;
        }

        const nextPoint: Point = {
          x: xValues[nextXIndex],

          y: currentPoint.y,
        };

        if (this.segmentBlocked(currentPoint, nextPoint, obstacles)) {
          continue;
        }

        const nextNode = this.nodeIndex(nextXIndex, currentYIndex, xCount);

        this.relaxRouteState(
          currentNode,
          currentDirection,
          nextNode,
          1,
          currentPoint,
          nextPoint,
          goal,
          gScore,
          parent,
          parentDirection,
          open,
        );
      }

      /*
       * Vertical neighbors.
       */
      for (const deltaY of [-1, 1]) {
        const nextYIndex = currentYIndex + deltaY;

        if (nextYIndex < 0 || nextYIndex >= yCount) {
          continue;
        }

        const nextPoint: Point = {
          x: currentPoint.x,

          y: yValues[nextYIndex],
        };

        if (this.segmentBlocked(currentPoint, nextPoint, obstacles)) {
          continue;
        }

        const nextNode = this.nodeIndex(currentXIndex, nextYIndex, xCount);

        this.relaxRouteState(
          currentNode,
          currentDirection,
          nextNode,
          2,
          currentPoint,
          nextPoint,
          goal,
          gScore,
          parent,
          parentDirection,
          open,
        );
      }
    }

    if (goalState < 0) {
      return this.fallbackRoute(start, goal);
    }

    const states: number[] = [];

    let state = goalState;

    while (state >= 0) {
      states.push(state);

      const previousNode = parent[state];

      if (previousNode < 0) {
        break;
      }

      const previousDirection = parentDirection[state];

      state = this.stateIndex(previousNode, previousDirection);
    }

    states.reverse();

    const points = states.map((stateValue) => {
      const node = Math.floor(stateValue / 3);

      const xIndex = node % xCount;

      const yIndex = Math.floor(node / xCount);

      return {
        x: xValues[xIndex],

        y: yValues[yIndex],
      };
    });

    return this.removeCollinearPoints(points);
  }

  private relaxRouteState(
    currentNode: number,
    currentDirection: 0 | 1 | 2,
    nextNode: number,
    nextDirection: 1 | 2,
    currentPoint: Point,
    nextPoint: Point,
    goal: Point,
    gScore: number[],
    parent: number[],
    parentDirection: (0 | 1 | 2)[],
    open: MinHeap,
  ): void {
    const nextState = this.stateIndex(nextNode, nextDirection);

    const movementCost = this.distance(currentPoint, nextPoint);

    const bendCost =
      currentDirection !== 0 && currentDirection !== nextDirection ? this.bendPenalty : 0;

    const currentState = this.stateIndex(currentNode, currentDirection);

    const tentative = gScore[currentState] + movementCost + bendCost;

    if (tentative >= gScore[nextState]) {
      return;
    }

    gScore[nextState] = tentative;

    parent[nextState] = currentNode;

    parentDirection[nextState] = currentDirection;

    const heuristic = this.manhattan(nextPoint, goal);

    open.push({
      state: nextState,
      priority: tentative + heuristic,
    });
  }

  private routeCoordinates(
    obstacles: Rect[],
    axis: 'x' | 'y',
    start: Point,
    goal: Point,
  ): number[] {
    const values = new Set<number>();

    if (axis === 'x') {
      values.add(start.x);
      values.add(goal.x);
      values.add(this.canvasMargin);
      values.add(this.canvasWidth - this.canvasMargin);

      for (const obstacle of obstacles) {
        values.add(obstacle.left);
        values.add(obstacle.right);
      }
    } else {
      values.add(start.y);
      values.add(goal.y);
      values.add(this.canvasMargin);
      values.add(this.canvasHeight - this.canvasMargin);

      for (const obstacle of obstacles) {
        values.add(obstacle.top);
        values.add(obstacle.bottom);
      }
    }

    return [...values].sort((a, b) => a - b);
  }

  private segmentBlocked(start: Point, end: Point, obstacles: Rect[]): boolean {
    if (Math.abs(start.x - end.x) < 0.001) {
      const x = start.x;

      const top = Math.min(start.y, end.y);

      const bottom = Math.max(start.y, end.y);

      return obstacles.some(
        (obstacle) =>
          x > obstacle.left && x < obstacle.right && bottom > obstacle.top && top < obstacle.bottom,
      );
    }

    if (Math.abs(start.y - end.y) < 0.001) {
      const y = start.y;

      const left = Math.min(start.x, end.x);

      const right = Math.max(start.x, end.x);

      return obstacles.some(
        (obstacle) =>
          y > obstacle.top && y < obstacle.bottom && right > obstacle.left && left < obstacle.right,
      );
    }

    return true;
  }

  private fallbackRoute(start: Point, goal: Point): Point[] {
    const horizontalFirst = this.removeCollinearPoints([
      start,
      {
        x: goal.x,
        y: start.y,
      },
      goal,
    ]);

    const verticalFirst = this.removeCollinearPoints([
      start,
      {
        x: start.x,
        y: goal.y,
      },
      goal,
    ]);

    return this.routeLength(horizontalFirst) <= this.routeLength(verticalFirst)
      ? horizontalFirst
      : verticalFirst;
  }

  private routeLength(points: Point[]): number {
    let total = 0;

    for (let index = 0; index < points.length - 1; index++) {
      total += this.distance(points[index], points[index + 1]);
    }

    return total;
  }

  private offsetPoint(point: ConnectionPoint, distance: number): Point {
    switch (point.side) {
      case 'top':
        return {
          x: point.x,
          y: point.y - distance,
        };

      case 'right':
        return {
          x: point.x + distance,
          y: point.y,
        };

      case 'bottom':
        return {
          x: point.x,
          y: point.y + distance,
        };

      case 'left':
        return {
          x: point.x - distance,
          y: point.y,
        };
    }
  }

  /**
   * Cardinality is intentionally placed near the source.
   *
   * It walks along the actual route, so it never assumes
   * that the first segment is long enough.
   */
  private findLabelPoint(points: Point[]): Point {
    if (points.length < 2) {
      return (
        points[0] ?? {
          x: 0,
          y: 0,
        }
      );
    }

    let remaining = this.labelDistance;

    for (let index = 0; index < points.length - 1; index++) {
      const start = points[index];

      const end = points[index + 1];

      const segmentLength = this.distance(start, end);

      if (segmentLength <= 0) {
        continue;
      }

      if (remaining <= segmentLength) {
        return this.moveToward(start, end, remaining);
      }

      remaining -= segmentLength;
    }

    const lastIndex = points.length - 1;

    const start = points[lastIndex - 1];

    const end = points[lastIndex];

    return this.moveToward(start, end, Math.min(24, this.distance(start, end) / 2));
  }

  private roundedPolyline(points: Point[], radius: number): string {
    if (points.length === 0) {
      return '';
    }

    if (points.length === 1) {
      return `M ${points[0].x} ${points[0].y}`;
    }

    let path = `M ${points[0].x} ${points[0].y}`;

    for (let index = 1; index < points.length - 1; index++) {
      const previous = points[index - 1];

      const current = points[index];

      const next = points[index + 1];

      const incomingLength = this.distance(previous, current);

      const outgoingLength = this.distance(current, next);

      const corner = Math.min(radius, incomingLength / 2, outgoingLength / 2);

      const before = this.moveToward(current, previous, corner);

      const after = this.moveToward(current, next, corner);

      path += ` L ${before.x} ${before.y}` + ` Q ${current.x} ${current.y} ${after.x} ${after.y}`;
    }

    const last = points[points.length - 1];

    path += ` L ${last.x} ${last.y}`;

    return path;
  }

  private removeDuplicatePoints(points: Point[]): Point[] {
    const result: Point[] = [];

    for (const point of points) {
      const previous = result[result.length - 1];

      if (!previous || !this.samePoint(previous, point)) {
        result.push(point);
      }
    }

    return result;
  }

  private removeCollinearPoints(points: Point[]): Point[] {
    const deduplicated = this.removeDuplicatePoints(points);

    if (deduplicated.length <= 2) {
      return deduplicated;
    }

    const result: Point[] = [deduplicated[0]];

    for (let index = 1; index < deduplicated.length - 1; index++) {
      const previous = result[result.length - 1];

      const current = deduplicated[index];

      const next = deduplicated[index + 1];

      const sameVertical =
        Math.abs(previous.x - current.x) < 0.001 && Math.abs(current.x - next.x) < 0.001;

      const sameHorizontal =
        Math.abs(previous.y - current.y) < 0.001 && Math.abs(current.y - next.y) < 0.001;

      if (sameVertical || sameHorizontal) {
        continue;
      }

      result.push(current);
    }

    result.push(deduplicated[deduplicated.length - 1]);

    return result;
  }

  private connectionSide(source: CanvasEntity, target: CanvasEntity): ConnectionSide {
    const sourceCenter = this.entityCenter(source);

    const targetCenter = this.entityCenter(target);

    const deltaX = targetCenter.x - sourceCenter.x;

    const deltaY = targetCenter.y - sourceCenter.y;

    if (Math.abs(deltaX) >= Math.abs(deltaY)) {
      return deltaX >= 0 ? 'right' : 'left';
    }

    return deltaY >= 0 ? 'bottom' : 'top';
  }

  private entityCenter(entity: CanvasEntity): Point {
    return {
      x: entity.x + entity.width / 2,

      y: entity.y + entity.height / 2,
    };
  }

  private samePoint(first: Point, second: Point): boolean {
    return Math.abs(first.x - second.x) < 0.001 && Math.abs(first.y - second.y) < 0.001;
  }

  private distance(first: Point, second: Point): number {
    return Math.sqrt(Math.pow(second.x - first.x, 2) + Math.pow(second.y - first.y, 2));
  }

  private manhattan(first: Point, second: Point): number {
    return Math.abs(second.x - first.x) + Math.abs(second.y - first.y);
  }

  private moveToward(from: Point, to: Point, distance: number): Point {
    const total = this.distance(from, to);

    if (total === 0 || distance <= 0) {
      return {
        x: from.x,
        y: from.y,
      };
    }

    const ratio = Math.min(1, distance / total);

    return {
      x: from.x + (to.x - from.x) * ratio,

      y: from.y + (to.y - from.y) * ratio,
    };
  }

  private cardinalityForRelationship(relationship: ModelRelationship): string {
    if (relationship.sourceCardinality && relationship.targetCardinality) {
      return `${relationship.sourceCardinality}..${relationship.targetCardinality}`;
    }

    switch (relationship.type) {
      case 'ONE_TO_ONE':
        return '1..1';

      case 'ONE_TO_MANY':
        return '1..N';

      case 'MANY_TO_ONE':
        return 'N..1';

      case 'MANY_TO_MANY':
        return 'N..N';

      default:
        return '?..?';
    }
  }

  private stateIndex(node: number, direction: 0 | 1 | 2): number {
    return node * 3 + direction;
  }

  private nodeIndex(xIndex: number, yIndex: number, xCount: number): number {
    return yIndex * xCount + xIndex;
  }

  private coordinateIndex(values: number[], value: number): number {
    const exact = values.findIndex((candidate) => Math.abs(candidate - value) < 0.001);

    if (exact >= 0) {
      return exact;
    }

    let best = 0;
    let bestDistance = Number.POSITIVE_INFINITY;

    for (let index = 0; index < values.length; index++) {
      const distance = Math.abs(values[index] - value);

      if (distance < bestDistance) {
        bestDistance = distance;
        best = index;
      }
    }

    return best;
  }
}

class MinHeap {
  private readonly items: HeapItem[] = [];

  push(item: HeapItem): void {
    this.items.push(item);

    let index = this.items.length - 1;

    while (index > 0) {
      const parent = Math.floor((index - 1) / 2);

      if (this.items[parent].priority <= this.items[index].priority) {
        break;
      }

      [this.items[parent], this.items[index]] = [this.items[index], this.items[parent]];

      index = parent;
    }
  }

  pop(): HeapItem | undefined {
    if (this.items.length === 0) {
      return undefined;
    }

    const first = this.items[0];

    const last = this.items.pop();

    if (this.items.length > 0 && last) {
      this.items[0] = last;

      let index = 0;

      while (true) {
        const left = index * 2 + 1;

        const right = left + 1;

        let smallest = index;

        if (left < this.items.length && this.items[left].priority < this.items[smallest].priority) {
          smallest = left;
        }

        if (
          right < this.items.length &&
          this.items[right].priority < this.items[smallest].priority
        ) {
          smallest = right;
        }

        if (smallest === index) {
          break;
        }

        [this.items[index], this.items[smallest]] = [this.items[smallest], this.items[index]];

        index = smallest;
      }
    }

    return first;
  }

  isEmpty(): boolean {
    return this.items.length === 0;
  }
}
