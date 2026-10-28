import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';
import { WorkflowContentComponent } from '../../shared/components/workflow-content/workflow-content.component';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';
import { VisualSpecificationComponent } from './components/visual-specification/visual-specification.component';
import { ValidationFindingsComponent } from './components/validation-findings/validation-findings.component';
import { AuthoringInputComponent } from './components/authoring-input/authoring-input.component';
import { WorkspaceHeaderComponent } from '../../shared/components/workspace-header/workspace-header.component';
import { DecisionSupportComponent } from './components/decision-support/decision-support.component';
import { AssumptionsReviewComponent } from './components/assumptions-review/assumptions-review.component';

import { AIService } from '../../core/services/ai.service';
import { SpecificationService } from '../../core/services/specification.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  AIWholeSpecificationDecisionItem,
  AIWholeSpecificationProposalResponse,
} from '../../core/interfaces/ai-whole-specification-proposal.interface';

type RecommendationReviewStatus = 'pending' | 'accepted' | 'rejected';

interface RecommendationReviewState {
  value: string;
  draftValue: string;
  status: RecommendationReviewStatus;
  editing: boolean;
}

@Component({
  selector: 'app-specification-authoring',
  standalone: true,
  imports: [WorkflowPageHeaderComponent, WorkflowContentComponent, WorkflowActionBarComponent, VisualSpecificationComponent, ValidationFindingsComponent, AuthoringInputComponent, WorkspaceHeaderComponent, DecisionSupportComponent, AssumptionsReviewComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './specification-authoring.component.html',
  styleUrl: './specification-authoring.component.css',
})
export class SpecificationAuthoringComponent {
  private readonly aiService = inject(AIService);
  private readonly specificationService = inject(SpecificationService);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly dataModelId = this.route.snapshot.paramMap.get('dataModelId') ?? '';

  readonly prompt = signal('');
  readonly proposal = signal<AIWholeSpecificationProposalResponse | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly requestInProgress = signal(false);
  readonly saveInProgress = signal(false);
  readonly recommendationReviews = signal<Record<string, RecommendationReviewState>>({});
  readonly clarificationAnswers = signal<Record<string, string>>({});
  readonly enrichedDescription = signal('');
  readonly showDescriptionGuide = signal(false);

  readonly orderManagementExampleDescription = `ORDER MANAGEMENT DATA MODEL

PURPOSE
Create a synthetic dataset for testing a simple order management system. The model must represent customers, products, sales orders, and the individual product lines belonging to each sales order.

ENTITIES AND FIELDS

CUSTOMER
Represent a customer who can place sales orders.
Fields:
- CUSTOMER_ID: IDENTIFIER. Uniquely identifies each customer.
- CUSTOMER_NAME: STRING. The customer's name.
- CUSTOMER_EMAIL: STRING. The customer's email address.
- CUSTOMER_STATUS: CATEGORICAL. Allowed values: ACTIVE, INACTIVE.
Entity identity: CUSTOMER_ID.
Requested population: 1,000 customers.

PRODUCT
Represent a product that can be ordered.
Fields:
- PRODUCT_ID: IDENTIFIER. Uniquely identifies each product.
- PRODUCT_NAME: STRING. The product's name.
- PRODUCT_CATEGORY: CATEGORICAL. Allowed values: HARDWARE, SOFTWARE, ACCESSORY.
- UNIT_PRICE: DECIMAL. The product's unit price.
Entity identity: PRODUCT_ID.
Requested population: 200 products.

SALES_ORDER
Represent an order placed by one customer.
Fields:
- SALES_ORDER_ID: IDENTIFIER. Uniquely identifies each sales order.
- CUSTOMER_ID: IDENTIFIER. References the customer who placed the order.
- ORDER_STATUS: CATEGORICAL. Allowed values: DRAFT, CONFIRMED, SHIPPED, CANCELLED.
Entity identity: SALES_ORDER_ID.
Requested population: 3,000 sales orders.

ORDER_LINE
Represent one product line within a sales order.
Fields:
- ORDER_LINE_ID: IDENTIFIER. Uniquely identifies each order line.
- SALES_ORDER_ID: IDENTIFIER. References the sales order containing this line.
- PRODUCT_ID: IDENTIFIER. References the product on this line.
- QUANTITY: INTEGER. The quantity ordered.
- UNIT_PRICE: DECIMAL. The unit price recorded for this order line.
Entity identity: ORDER_LINE_ID.
Requested population: 6,000 order lines.

RELATIONSHIPS
- One CUSTOMER can have many SALES_ORDER records. Each SALES_ORDER belongs to exactly one CUSTOMER.
- One SALES_ORDER can have many ORDER_LINE records. Each ORDER_LINE belongs to exactly one SALES_ORDER.
- One PRODUCT can be referenced by many ORDER_LINE records. Each ORDER_LINE references exactly one PRODUCT.

FOREIGN KEYS
- SALES_ORDER.CUSTOMER_ID references CUSTOMER.CUSTOMER_ID.
- ORDER_LINE.SALES_ORDER_ID references SALES_ORDER.SALES_ORDER_ID.
- ORDER_LINE.PRODUCT_ID references PRODUCT.PRODUCT_ID.

CONSTRAINTS
- PRODUCT.UNIT_PRICE must be greater than 0.
- ORDER_LINE.QUANTITY must be greater than or equal to 1.
- ORDER_LINE.UNIT_PRICE must be greater than 0.
- The categorical fields must use only the allowed values listed above.

GENERATION REQUIREMENTS
Generate the requested population for each entity while preserving entity identities and foreign-key referential integrity. Every SALES_ORDER must reference an existing CUSTOMER. Every ORDER_LINE must reference an existing SALES_ORDER and PRODUCT. Do not create foreign-key values that reference missing records.

REVIEW AND CLARIFICATION
Use the requirements above as the source of truth. Do not silently add business rules that were not specified. If a requirement is ambiguous, unsupported by the current FORGE specification capabilities, or needs a decision, identify it for review instead of inventing a value or rule.

Treat this as a starting example. I may change the entities, fields, field types, allowed values, constraints, relationships, foreign keys, and requested populations to match my own system.`;


  readonly decisionItems = computed(() => this.proposal()?.decision_items ?? []);



  readonly requiredDecisionsComplete = computed(() =>
    this.decisionItems()
      .filter((item) => item.required)
      .every((item) => (this.clarificationAnswers()[item.id] ?? '').trim().length > 0),
  );


  asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {};
  }

  asArray(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
  }

  displayValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'Not specified';
    }
    if (Array.isArray(value)) {
      return value.map((item) => this.displayValue(item)).join(', ');
    }
    if (typeof value === 'object') {
      return 'Configured';
    }
    return String(value);
  }

  populationCount(entity: unknown): string {
    const population = this.asRecord(this.asRecord(entity)['population']);
    const count = population['count'];
    return count === null || count === undefined
      ? 'Not specified'
      : this.displayValue(count);
  }

  identityFields(entity: unknown): string {
    const identity = this.asRecord(this.asRecord(entity)['identity']);
    const fields = this.asArray(identity['fields']);
    return fields.length
      ? fields.map((field) => this.displayValue(field)).join(' + ')
      : 'Identity needs review';
  }

  fieldIdentityStrategy(field: unknown): string {
    const identity = this.asRecord(this.asRecord(field)['identity']);
    return this.displayValue(identity['strategy'] ?? null);
  }

  fieldGenerationSummary(field: unknown): string {
    const generation = this.asRecord(this.asRecord(field)['generation']);
    if (!Object.keys(generation).length) {
      return 'No field-level generation configuration';
    }

    const parts: string[] = [];
    for (const key of ['strategy', 'distribution', 'generator']) {
      const value = generation[key];
      if (value !== null && value !== undefined) {
        parts.push(`${this.humanize(key)}: ${this.displayValue(value)}`);
      }
    }

    const parameters = this.asRecord(generation['parameters']);
    for (const [key, value] of Object.entries(parameters)) {
      parts.push(`${this.humanize(key)}: ${this.displayValue(value)}`);
    }

    return parts.join(' · ') || 'Generation configured';
  }

  recordTitle(item: unknown, fallback: string): string {
    const record = this.asRecord(item);
    for (const key of ['name', 'title', 'entity', 'field', 'id']) {
      const value = record[key];
      if (typeof value === 'string' && value.trim()) {
        return value;
      }
    }
    return fallback;
  }

  recordSummary(item: unknown): string {
    const record = this.asRecord(item);

    if ('source' in record && 'target' in record) {
      const type = record['type'];
      const participation = [
        record['source_participation'],
        record['target_participation'],
      ].filter((value) => value !== undefined && value !== null);

      return [
        `${this.referenceText(record['source'])} → ${this.referenceText(record['target'])}`,
        type ? this.displayValue(type) : '',
        participation.length ? participation.map((value) => this.displayValue(value)).join(' / ') : '',
      ].filter(Boolean).join(' · ');
    }

    if ('operator' in record && 'field' in record) {
      const left = [
        record['entity'] ? this.displayValue(record['entity']) : '',
        this.displayValue(record['field']),
      ].filter(Boolean).join('.');
      return `${left} ${this.displayValue(record['operator'])} ${this.displayValue(record['value'])}`;
    }

    const ignored = new Set(['name', 'title', 'id']);
    const parts = Object.entries(record)
      .filter(([key, value]) =>
        !ignored.has(key) &&
        value !== null &&
        value !== undefined &&
        typeof value !== 'object',
      )
      .map(([key, value]) => `${this.humanize(key)}: ${this.displayValue(value)}`);

    return parts.join(' · ') || 'Details available for review';
  }

  referenceText(value: unknown): string {
    if (typeof value === 'string') {
      return value;
    }

    const record = this.asRecord(value);
    const entity = this.displayValue(record['entity']);
    const fields = this.asArray(record['fields'])
      .map((field) => this.displayValue(field))
      .join(' + ');

    return fields ? `${entity}.${fields}` : entity;
  }

  humanize(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }

  saveSpecification(): void {
    const proposal = this.proposal();

    if (
      !this.dataModelId ||
      !proposal?.specification ||
      !proposal.validation.can_continue ||
      this.requestInProgress() ||
      this.saveInProgress()
    ) {
      return;
    }

    this.saveInProgress.set(true);
    this.errorMessage.set(null);

    this.specificationService
      .saveSpecification(this.dataModelId, proposal.specification)
      .subscribe({
        next: () => {
          this.notificationService.success(
            'Specification saved',
            'Specification saved successfully.',
          );
          void this.router.navigate([
            '/workspace',
            this.dataModelId,
            'model-studio',
          ]);
          this.saveInProgress.set(false);
        },
        error: (error: unknown) => {
          const detail =
            error instanceof HttpErrorResponse &&
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'FORGE could not save the specification. Review validation findings and try again.';

          this.errorMessage.set(detail);
          this.saveInProgress.set(false);
        },
      });
  }

  returnToModelStudio(): void {
    if (!this.dataModelId) {
      return;
    }

    void this.router.navigate([
      '/workspace',
      this.dataModelId,
      'model-studio',
    ]);
  }

  toggleDescriptionGuide(): void {
    this.showDescriptionGuide.update((visible) => !visible);
  }

  useOrderManagementExample(): void {
    if (this.requestInProgress()) {
      return;
    }

    if (
      this.prompt().trim() &&
      !window.confirm('Replace the current description with the illustrative PLM example?')
    ) {
      return;
    }

    this.updatePrompt(this.orderManagementExampleDescription);
    this.showDescriptionGuide.set(false);
  }

  generateProposal(promptOverride?: string): void {
    const prompt = (promptOverride ?? this.prompt()).trim();

    if (!prompt || this.requestInProgress()) {
      return;
    }

    this.requestInProgress.set(true);
    this.errorMessage.set(null);
    this.proposal.set(null);
    this.recommendationReviews.set({});
    this.clarificationAnswers.set({});
    if (promptOverride === undefined) {
      this.enrichedDescription.set('');
    }

    this.aiService.proposeWholeSpecification(prompt).subscribe({
      next: (response) => {
        this.proposal.set(response);
        this.clarificationAnswers.set(
          Object.fromEntries(
            response.decision_items.map((item) => [
              item.id,
              '',
            ]),
          ),
        );
        this.recommendationReviews.set(
          Object.fromEntries(
            response.recommendations.map((recommendation) => [
              recommendation.id,
              {
                value: recommendation.proposed_value,
                draftValue: recommendation.proposed_value,
                status: 'pending' as RecommendationReviewStatus,
                editing: false,
              },
            ]),
          ),
        );
        this.requestInProgress.set(false);
      },
      error: (error: unknown) => {
        const detail =
          error instanceof HttpErrorResponse &&
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'FORGE could not generate a proposal. Check the connection and try again.';

        this.errorMessage.set(detail);
        this.requestInProgress.set(false);
      },
    });
  }

  updatePrompt(value: string): void {
    this.prompt.set(value);
    this.enrichedDescription.set('');
  }

  clearDraft(): void {
    if (this.requestInProgress()) {
      return;
    }

    this.prompt.set('');
    this.proposal.set(null);
    this.errorMessage.set(null);
    this.recommendationReviews.set({});
    this.clarificationAnswers.set({});
    this.enrichedDescription.set('');
  }

  applyDecisionRecommendation(id: string, proposedValue: string): void {
    if (this.requestInProgress() || !proposedValue.trim()) {
      return;
    }

    this.updateClarificationAnswer(id, proposedValue);
  }

  updateClarificationAnswer(id: string, value: string): void {
    this.clarificationAnswers.update((answers) => ({
      ...answers,
      [id]: value,
    }));
    this.enrichedDescription.set('');
  }

  buildEnrichedDescription(): void {
    const original = this.prompt().trim();
    const items = this.decisionItems();
    const answers = this.clarificationAnswers();

    if (!original || !items.length || !this.requiredDecisionsComplete()) {
      return;
    }

    const decisions = items
      .filter((item) => (answers[item.id] ?? '').trim().length > 0)
      .map((item) => `- ${item.question}\n  Answer: ${answers[item.id].trim()}`);

    const updatedDescription =
      `${original}\n\nConfirmed user decisions:\n${decisions.join('\n')}`;

    this.prompt.set(updatedDescription);
    this.enrichedDescription.set(updatedDescription);
    this.generateProposal(updatedDescription);
  }

  generateProposalFromEnrichedDescription(): void {
    if (!this.prompt().trim() || this.requestInProgress()) {
      return;
    }

    this.generateProposal();
  }

  reviewFor(id: string): RecommendationReviewState | undefined {
    return this.recommendationReviews()[id];
  }

  reviewCount(status: RecommendationReviewStatus): number {
    return Object.values(this.recommendationReviews()).filter(
      (review) => review.status === status,
    ).length;
  }

  acceptRecommendation(id: string): void {
    this.updateRecommendationReview(id, {
      status: 'accepted',
      editing: false,
    });
  }

  rejectRecommendation(id: string): void {
    this.updateRecommendationReview(id, {
      status: 'rejected',
      editing: false,
      draftValue: this.recommendationReviews()[id]?.value ?? '',
    });
  }

  startRecommendationEdit(id: string): void {
    const review = this.recommendationReviews()[id];
    if (!review) {
      return;
    }

    this.updateRecommendationReview(id, {
      draftValue: review.value,
      editing: true,
    });
  }

  updateRecommendationDraft(id: string, value: string): void {
    this.updateRecommendationReview(id, { draftValue: value });
  }

  saveRecommendationEdit(id: string): void {
    const review = this.recommendationReviews()[id];
    if (!review || !review.draftValue.trim()) {
      return;
    }

    this.updateRecommendationReview(id, {
      value: review.draftValue.trim(),
      draftValue: review.draftValue.trim(),
      status: 'accepted',
      editing: false,
    });
  }

  cancelRecommendationEdit(id: string): void {
    const review = this.recommendationReviews()[id];
    if (!review) {
      return;
    }

    this.updateRecommendationReview(id, {
      draftValue: review.value,
      editing: false,
    });
  }

  private updateRecommendationReview(
    id: string,
    changes: Partial<RecommendationReviewState>,
  ): void {
    this.recommendationReviews.update((reviews) => {
      const current = reviews[id];
      if (!current) {
        return reviews;
      }

      return {
        ...reviews,
        [id]: { ...current, ...changes },
      };
    });
  }
}
