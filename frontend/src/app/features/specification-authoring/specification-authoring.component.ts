import {
  ChangeDetectionStrategy,
  Component,
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
import { AssumptionsReviewComponent } from './components/assumptions-review/assumptions-review.component';

import { AIService } from '../../core/services/ai.service';
import { SpecificationService } from '../../core/services/specification.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  AIWholeSpecificationProposalResponse,
} from '../../core/interfaces/ai-whole-specification-proposal.interface';

@Component({
  selector: 'app-specification-authoring',
  standalone: true,
  imports: [WorkflowPageHeaderComponent, WorkflowContentComponent, WorkflowActionBarComponent, VisualSpecificationComponent, ValidationFindingsComponent, AuthoringInputComponent, WorkspaceHeaderComponent, AssumptionsReviewComponent],
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


  acceptDraftAndContinue(): void {
    const proposal = this.proposal();

    if (
      !this.dataModelId ||
      !proposal?.specification ||
      typeof proposal.specification !== 'object' ||
      this.requestInProgress() ||
      this.saveInProgress()
    ) {
      return;
    }

    this.saveInProgress.set(true);
    this.errorMessage.set(null);

    this.specificationService
      .saveSpecification(
        this.dataModelId,
        proposal.specification as Record<string, unknown>,
      )
      .subscribe({
        next: () => {
          this.notificationService.success(
            'Specification saved',
            'Your generated specification is saved. Review and correct any validation findings in Model Studio.',
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
              : 'FORGE could not save the specification. Check the proposal structure and try again.';

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

    this.aiService.proposeWholeSpecification(prompt).subscribe({
      next: (response) => {
        this.proposal.set(response);
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
  }

  clearDraft(): void {
    if (this.requestInProgress()) {
      return;
    }

    this.prompt.set('');
    this.proposal.set(null);
    this.errorMessage.set(null);
  }


}
