import {
  CanvasEntity,
  ModelRelationship,
} from '../models/model-studio.models';

import {
  MODEL_NODE_HEIGHT,
  MODEL_NODE_WIDTH,
} from './model-geometry';

interface LayoutOptions {
  horizontalGap: number;
  verticalGap: number;
  canvasPadding: number;
}

interface Position {
  x: number;
  y: number;
}

const DEFAULT_LAYOUT: LayoutOptions = {
  horizontalGap: Math.round(MODEL_NODE_WIDTH * 0.75),
  verticalGap: Math.round(MODEL_NODE_HEIGHT * 0.70),
  canvasPadding: Math.round(MODEL_NODE_WIDTH * 0.26),
};

function buildGraph(
  entities: readonly CanvasEntity[],
  relationships: readonly ModelRelationship[],
): Map<string, Set<string>> {
  const graph = new Map<string, Set<string>>();

  for (const entity of entities) {
    graph.set(entity.name, new Set<string>());
  }

  for (const relationship of relationships) {
    graph.get(relationship.source)?.add(relationship.target);
    graph.get(relationship.target)?.add(relationship.source);
  }

  return graph;
}

function rectangleOverlaps(
  position: Position,
  entities: readonly CanvasEntity[],
  placed: ReadonlyMap<string, Position>,
  gapX: number,
  gapY: number,
): boolean {
  const candidateLeft = position.x - gapX;
  const candidateRight =
    position.x + MODEL_NODE_WIDTH + gapX;
  const candidateTop = position.y - gapY;
  const candidateBottom =
    position.y + MODEL_NODE_HEIGHT + gapY;

  for (const entity of entities) {
    const existing = placed.get(entity.name);

    if (!existing) {
      continue;
    }

    const existingRight =
      existing.x + MODEL_NODE_WIDTH;
    const existingBottom =
      existing.y + MODEL_NODE_HEIGHT;

    const separated =
      candidateRight <= existing.x ||
      candidateLeft >= existingRight ||
      candidateBottom <= existing.y ||
      candidateTop >= existingBottom;

    if (!separated) {
      return true;
    }
  }

  return false;
}

function distance(
  first: Position,
  second: Position,
): number {
  const dx = first.x - second.x;
  const dy = first.y - second.y;

  return Math.sqrt(dx * dx + dy * dy);
}

function candidatePositions(
  neighbours: readonly Position[],
  options: LayoutOptions,
): Position[] {
  const candidates: Position[] = [];

  const horizontalStep =
    MODEL_NODE_WIDTH + options.horizontalGap;

  const verticalStep =
    MODEL_NODE_HEIGHT + options.verticalGap;

  for (const neighbour of neighbours) {
    candidates.push(
      {
        x: neighbour.x + horizontalStep,
        y: neighbour.y,
      },
      {
        x: neighbour.x - horizontalStep,
        y: neighbour.y,
      },
    );
  }

  for (const neighbour of neighbours) {
    candidates.push(
      {
        x: neighbour.x + horizontalStep,
        y: neighbour.y + verticalStep,
      },
      {
        x: neighbour.x + horizontalStep,
        y: neighbour.y - verticalStep,
      },
      {
        x: neighbour.x - horizontalStep,
        y: neighbour.y + verticalStep,
      },
      {
        x: neighbour.x - horizontalStep,
        y: neighbour.y - verticalStep,
      },
    );
  }

  for (const neighbour of neighbours) {
    candidates.push(
      {
        x: neighbour.x,
        y: neighbour.y + verticalStep,
      },
      {
        x: neighbour.x,
        y: neighbour.y - verticalStep,
      },
    );
  }

  return candidates;
}

function scoreCandidate(
  candidate: Position,
  neighbours: readonly Position[],
): number {
  if (neighbours.length === 0) {
    return 0;
  }

  return neighbours.reduce(
    (total, neighbour) => {
      const distanceScore =
        distance(candidate, neighbour);

      const verticallyAligned =
        candidate.x === neighbour.x;

      const verticalAlignmentPenalty =
        verticallyAligned
          ? MODEL_NODE_WIDTH
          : 0;

      return (
        total +
        distanceScore +
        verticalAlignmentPenalty
      );
    },
    0,
  );
}

function findBestPosition(
  entity: CanvasEntity,
  graph: ReadonlyMap<string, Set<string>>,
  placed: ReadonlyMap<string, Position>,
  entities: readonly CanvasEntity[],
  options: LayoutOptions,
): Position {
  const neighbours = [
    ...(graph.get(entity.name) ?? []),
  ]
    .map(name => placed.get(name))
    .filter(
      (position): position is Position =>
        position !== undefined,
    );

  if (neighbours.length === 0) {
    return {
      x: options.canvasPadding,
      y: options.canvasPadding,
    };
  }

  const candidates = candidatePositions(
    neighbours,
    options,
  );

  const validCandidates = candidates.filter(
    candidate =>
      candidate.x >= options.canvasPadding &&
      candidate.y >= options.canvasPadding &&
      !rectangleOverlaps(
        candidate,
        entities,
        placed,
        0,
        0,
      ),
  );

  if (validCandidates.length === 0) {
    const fallbackCandidates: Position[] = [];

    for (const neighbour of neighbours) {
      const horizontalStep =
        MODEL_NODE_WIDTH + options.horizontalGap;

      const verticalStep =
        MODEL_NODE_HEIGHT + options.verticalGap;

      for (let ring = 1; ring <= 4; ring++) {
        fallbackCandidates.push(
          {
            x: neighbour.x + horizontalStep * ring,
            y: neighbour.y,
          },
          {
            x: neighbour.x - horizontalStep * ring,
            y: neighbour.y,
          },
          {
            x: neighbour.x,
            y: neighbour.y + verticalStep * ring,
          },
          {
            x: neighbour.x,
            y: neighbour.y - verticalStep * ring,
          },
        );
      }
    }

    const validFallbacks =
      fallbackCandidates.filter(
        candidate =>
          candidate.x >= options.canvasPadding &&
          candidate.y >= options.canvasPadding &&
          !rectangleOverlaps(
            candidate,
            entities,
            placed,
            0,
            0,
          ),
      );

    if (validFallbacks.length > 0) {
      return validFallbacks.sort(
        (a, b) =>
          scoreCandidate(a, neighbours) -
          scoreCandidate(b, neighbours),
      )[0];
    }

    return {
      x: options.canvasPadding,
      y: options.canvasPadding,
    };
  }

  return validCandidates.sort(
    (a, b) =>
      scoreCandidate(a, neighbours) -
      scoreCandidate(b, neighbours),
  )[0];
}

function compactToPositiveSpace(
  positions: Map<string, Position>,
  options: LayoutOptions,
): Map<string, Position> {
  if (positions.size === 0) {
    return positions;
  }

  const minX = Math.min(
    ...[...positions.values()].map(
      position => position.x,
    ),
  );

  const minY = Math.min(
    ...[...positions.values()].map(
      position => position.y,
    ),
  );

  const offsetX =
    minX < options.canvasPadding
      ? options.canvasPadding - minX
      : 0;

  const offsetY =
    minY < options.canvasPadding
      ? options.canvasPadding - minY
      : 0;

  return new Map(
    [...positions.entries()].map(
      ([name, position]) => [
        name,
        {
          x: position.x + offsetX,
          y: position.y + offsetY,
        },
      ],
    ),
  );
}

export function layoutModel(
  entities: readonly CanvasEntity[],
  relationships: readonly ModelRelationship[],
  options: Partial<LayoutOptions> = {},
): CanvasEntity[] {
  const layout: LayoutOptions = {
    ...DEFAULT_LAYOUT,
    ...options,
  };

  if (entities.length === 0) {
    return [];
  }

  const graph = buildGraph(
    entities,
    relationships,
  );

  const anchor = [...entities].sort(
    (first, second) =>
      (graph.get(second.name)?.size ?? 0) -
      (graph.get(first.name)?.size ?? 0),
  )[0];

  const placed = new Map<string, Position>();

  placed.set(anchor.name, {
    x: layout.canvasPadding,
    y: layout.canvasPadding,
  });

  const remaining = new Set(
    entities
      .map(entity => entity.name)
      .filter(name => name !== anchor.name),
  );

  while (remaining.size > 0) {
    const nextEntity = [...remaining]
      .map(name => {
        const neighbours =
          graph.get(name) ?? new Set<string>();

        const positionedNeighbourCount =
          [...neighbours].filter(
            neighbour => placed.has(neighbour),
          ).length;

        const totalNeighbourCount =
          neighbours.size;

        return {
          name,
          positionedNeighbourCount,
          totalNeighbourCount,
        };
      })
      .sort(
        (first, second) =>
          second.positionedNeighbourCount -
            first.positionedNeighbourCount ||
          second.totalNeighbourCount -
            first.totalNeighbourCount,
      )[0];

    const entity = entities.find(
      item => item.name === nextEntity.name,
    )!;

    const position = findBestPosition(
      entity,
      graph,
      placed,
      entities,
      layout,
    );

    placed.set(entity.name, position);
    remaining.delete(entity.name);
  }

  const normalized =
    compactToPositiveSpace(
      placed,
      layout,
    );

  return entities.map(entity => {
    const position =
      normalized.get(entity.name)!;

    return {
      ...entity,
      x: position.x,
      y: position.y,
      width: MODEL_NODE_WIDTH,
      height: MODEL_NODE_HEIGHT,
    };
  });
}
