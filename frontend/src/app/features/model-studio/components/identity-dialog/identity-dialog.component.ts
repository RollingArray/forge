import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { AIIdentityProposal } from '../../../../core/interfaces/ai-identity-proposal.interface';
import { AIService } from '../../../../core/services/ai.service';
import { ForgeSpecificationEntity } from '../../../../core/interfaces/forge-specification-entity.interface';
import { ChoiceDividerComponent } from '../../../../shared/components/choice-divider/choice-divider.component';
import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';
import { IdentityAiAssistPanelComponent } from '../identity-ai-assist-panel/identity-ai-assist-panel.component';


@Component({
  selector: 'app-model-studio-identity-dialog',
  standalone: true,
  imports: [
    FormDialogComponent,
    ChoiceDividerComponent,
    IdentityAiAssistPanelComponent,
  ],
  templateUrl: './identity-dialog.component.html',
  styleUrl: './identity-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IdentityDialogComponent {
  private readonly aiService = inject(AIService);

  readonly dataModelId = input.required<string>();
  readonly entity = input.required<ForgeSpecificationEntity>();

  readonly closed = output<void>();
  readonly saved = output<string[]>();
  readonly proposalAccepted = output<void>();

  readonly selectedFields = signal<string[]>([]);
  readonly searchTerm = signal('');

  readonly aiGenerating = signal(false);
  readonly aiProposal = signal<AIIdentityProposal | null>(null);
  readonly aiProposalId = signal<string | null>(null);
  readonly aiProposalStatus = signal<
    'PROPOSE' | 'CLARIFY' | 'UNSUPPORTED' | null
  >(null);
  readonly aiProposalMessage = signal('');
  readonly aiProposalError = signal('');
  readonly aiPrompt = signal('');

  constructor() {
    effect(() => {
      const entity = this.entity();

      this.selectedFields.set([
        ...(entity.identity?.fields ?? []),
      ]);
      this.searchTerm.set('');
      this.clearAiState();
    });
  }

  identityFields(): string[] {
    return this.entity().identity?.fields ?? [];
  }

  availableFields(): string[] {
    const search = this.searchTerm().trim().toLowerCase();

    return this.entity().fields
      .map((field) => field.name)
      .filter((name) =>
        search ? name.toLowerCase().includes(search) : true,
      );
  }

  isSelected(fieldName: string): boolean {
    return this.selectedFields().includes(fieldName);
  }

  toggleField(fieldName: string): void {
    this.selectedFields.update((fields) =>
      fields.includes(fieldName)
        ? fields.filter((field) => field !== fieldName)
        : [...fields, fieldName],
    );
  }

  handleAiGenerate(request: string, regenerate = false): void {
    const trimmedRequest = request.trim();

    if (!trimmedRequest || this.aiGenerating()) {
      return;
    }

    this.aiPrompt.set(trimmedRequest);
    this.aiGenerating.set(true);
    this.aiProposal.set(null);
    this.aiProposalId.set(null);
    this.aiProposalStatus.set(null);
    this.aiProposalMessage.set('');
    this.aiProposalError.set('');

    this.aiService
      .proposeIdentity({
      dataModelId: this.dataModelId(),
        regenerate,
        mode: this.identityFields().length > 0 ? 'EDIT' : 'CREATE',
        entityName: this.entity().name,
        fields: this.entity().fields.map((field) => ({
          name: field.name,
          type: field.type,
          identity: field.identity ?? null,
        })),
        request: trimmedRequest,
        existingIdentity:
          this.identityFields().length > 0
            ? { fields: this.identityFields() }
            : null,
      })
      .subscribe({
        next: (response) => {
          this.aiProposalStatus.set(response.status);
          this.aiProposalMessage.set(response.message);
          this.aiProposalId.set(response.proposalId);
          this.aiProposal.set(response.proposal);
          this.aiGenerating.set(false);
        },
        error: (error: unknown) => {
          this.aiGenerating.set(false);
          this.aiProposalError.set(
            error instanceof Error
              ? error.message
              : 'FORGE AI could not generate an identity proposal.',
          );
        },
      });
  }

  regenerateAiProposal(): void {
    this.handleAiGenerate(this.aiPrompt(), true);
  }

  private recordProposalAccepted(proposalId: string): void {
    this.aiService.recordProposalActivity(
      this.dataModelId(),
      'identity',
      'ACCEPTED',
      proposalId,
    ).subscribe({
      error: (error: unknown) => {
        console.warn('[FORGE] Unable to record AI proposal acceptance.', error);
      },
    });
  }

  useAiProposal(): void {
    const proposal = this.aiProposal();
    const proposalId = this.aiProposalId();

    if (!proposal || !proposalId) {
      return;
    }

    this.selectedFields.set([...proposal.fields]);
    this.proposalAccepted.emit();
    this.recordProposalAccepted(proposalId);
  }

  save(): void {
    const fields = this.selectedFields();

    if (fields.length === 0) {
      return;
    }

    this.saved.emit(fields);
  }

  close(): void {
    this.closed.emit();
  }

  clearAiState(): void {
    this.aiGenerating.set(false);
    this.aiProposal.set(null);
    this.aiProposalId.set(null);
    this.aiProposalStatus.set(null);
    this.aiProposalMessage.set('');
    this.aiProposalError.set('');
    this.aiPrompt.set('');
  }
}
