import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { Location } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { marked } from 'marked';

import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';
import { ContentCardComponent } from '../../shared/components/content-card/content-card.component';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';
import { WorkspaceScrollAreaComponent } from '../../shared/components/workspace-scroll-area/workspace-scroll-area.component';

interface HelpArticle {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly category: string;
  readonly icon: string;
  readonly path: string;
  readonly keywords: readonly string[];
}

interface HelpSection {
  readonly id: string;
  readonly title: string;
  readonly depth: number;
}

@Component({
  selector: 'app-help-center',
  standalone: true,
  imports: [
    WorkflowPageHeaderComponent,
    ContentCardComponent,
    WorkflowActionBarComponent,
    WorkspaceScrollAreaComponent,
  ],
  templateUrl: './help-center.component.html',
  styleUrl: './help-center.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HelpCenterComponent {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly location = inject(Location);
  private readonly destroyRef = inject(DestroyRef);

  @ViewChild('articleScrollArea', { read: ElementRef })
  private articleScrollArea?: ElementRef<HTMLElement>;

  readonly searchTerm = signal('');
  readonly selectedArticleId = signal('forge-terminology');
  readonly articleMarkdown = signal('');
  readonly articleHtml = signal('');
  readonly articleSections = signal<HelpSection[]>([]);
  readonly selectedSectionId = signal('');
  readonly sectionLinkCopied = signal(false);
  readonly articleLoading = signal(true);
  readonly articleError = signal<string | null>(null);

  readonly articles: readonly HelpArticle[] = [
    {
      id: 'forge-terminology',
      title: 'FORGE Knowledge Guide',
      description:
        'Understand the concepts, vocabulary and rules behind specification-driven synthetic data generation.',
      category: 'FOUNDATIONS',
      icon: 'menu_book',
      path: '/assets/docs/forge-terminology.md',
      keywords: [
        'data model',
        'specification',
        'entity',
        'field',
        'identity',
        'generation',
        'distribution',
        'foreign key',
        'relationship',
        'constraint',
        'population',
        'csv',
        'validation',
      ],
    },
  ];

  readonly selectedArticle = computed(
    () =>
      this.articles.find(
        (article) => article.id === this.selectedArticleId(),
      ) ?? this.articles[0],
  );

  readonly filteredSections = computed(() => {
    const query = this.searchTerm().trim().toLowerCase();

    if (!query) {
      return this.articleSections();
    }

    return this.articleSections().filter((section) =>
      section.title.toLowerCase().includes(query),
    );
  });

  private loadedArticleId: string | null = null;

  constructor() {
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const requestedArticleId = params.get('article') ?? this.articles[0].id;
        const article =
          this.articles.find((item) => item.id === requestedArticleId) ??
          this.articles[0];
        const requestedSectionId = params.get('section');

        if (article.id !== this.loadedArticleId) {
          this.loadedArticleId = article.id;
          this.selectedArticleId.set(article.id);
          this.loadArticle(article, requestedSectionId);
          return;
        }

        if (requestedSectionId && this.articleMarkdown()) {
          this.scrollToSectionWhenReady(requestedSectionId);
        }
      });
  }

  onSearch(value: string): void {
    this.searchTerm.set(value);
  }

  clearSearch(): void {
    this.searchTerm.set('');
  }

  selectSection(section: HelpSection): void {
    this.selectedSectionId.set(section.id);

    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        article: this.selectedArticleId(),
        section: section.id,
      },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });

    this.scrollToSectionWhenReady(section.id);
  }

  copySectionLink(): void {
    const sectionId = this.selectedSectionId();

    if (!sectionId) {
      return;
    }

    const tree = this.router.createUrlTree(['/help'], {
      queryParams: {
        article: this.selectedArticleId(),
        section: sectionId,
      },
    });

    const url = `${window.location.origin}${this.router.serializeUrl(tree)}`;

    void navigator.clipboard.writeText(url).then(() => {
      this.sectionLinkCopied.set(true);
      window.setTimeout(() => this.sectionLinkCopied.set(false), 1800);
    });
  }

  private scrollToSectionWhenReady(sectionId: string): void {
    requestAnimationFrame(() => {
      const section = this.articleSections().find(
        (item) => item.id === sectionId,
      );

      if (section) {
        this.scrollToSection(section);
      }
    });
  }

  private scrollToSection(section: HelpSection): void {
    const host = this.articleScrollArea?.nativeElement;
    const scrollArea =
      host?.querySelector<HTMLElement>('.workspace-scroll-area');

    if (!scrollArea) {
      return;
    }

    const headings = Array.from(
      scrollArea.querySelectorAll<HTMLElement>(
        '.markdown-article h1, .markdown-article h2, .markdown-article h3',
      ),
    );

    const target = headings.find(
      (heading) => heading.textContent?.trim() === section.title,
    );

    if (!target) {
      console.warn('[Help Center] Article heading not found:', section.title);
      return;
    }

    const top =
      target.getBoundingClientRect().top -
      scrollArea.getBoundingClientRect().top +
      scrollArea.scrollTop -
      12;

    scrollArea.scrollTo({
      top: Math.max(0, top),
      behavior: 'smooth',
    });
  }

  goBack(): void {
    this.location.back();
  }

  goToWorkspace(): void {
    void this.router.navigate(['/workspace']);
  }

  retry(): void {
    this.loadArticle(this.selectedArticle());
  }

  private slugify(value: string): string {
    return value
      .toLowerCase()
      .replace(/[`*_~]/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/&amp;/g, 'and')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  private loadArticle(article: HelpArticle, requestedSectionId: string | null = null): void {
    this.articleLoading.set(true);
    this.articleError.set(null);
    this.articleMarkdown.set('');
    this.articleHtml.set('');
    this.articleSections.set([]);
    this.selectedSectionId.set('');

    this.http
      .get(article.path, { responseType: 'text' })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (markdown) => {
          try {
            const headingRecords: HelpSection[] = [];
            const headingCounts = new Map<string, number>();
            let documentTitleSkipped = false;

            for (const token of marked.lexer(markdown)) {
              if (token.type !== 'heading') {
                continue;
              }

              const title = token.text
                .replace(/[`*_~]/g, '')
                .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                .trim();

              const baseId = this.slugify(title);
              const occurrence = headingCounts.get(baseId) ?? 0;
              headingCounts.set(baseId, occurrence + 1);

              const id =
                occurrence === 0 ? baseId : `${baseId}-${occurrence + 1}`;

              headingRecords.push({
                id,
                title,
                depth: token.depth,
              });

              if (token.depth === 1 && !documentTitleSkipped) {
                documentTitleSkipped = true;
              }
            }

            const sections = headingRecords.filter(
              (heading, index) =>
                heading.depth === 1 &&
                !(index === 0 && documentTitleSkipped),
            );

            let headingIndex = 0;
            const html = marked
              .parse(markdown, { async: false })
              .replace(
                /<h([1-6])>([\s\S]*?)<\/h\1>/g,
                (match, depth: string, content: string) => {
                  const heading = headingRecords[headingIndex++];

                  return heading
                    ? `<h${depth} id="${heading.id}">${content}</h${depth}>`
                    : match;
                },
              );

            this.articleMarkdown.set(markdown);
            this.articleHtml.set(html);
            this.articleSections.set(sections);
            const initialSection =
              sections.find((section) => section.id === requestedSectionId) ??
              sections[0];

            this.selectedSectionId.set(initialSection?.id ?? '');
            this.articleLoading.set(false);

            if (requestedSectionId) {
              this.scrollToSectionWhenReady(requestedSectionId);
            }
          } catch {
            this.articleError.set('The article could not be rendered.');
            this.articleLoading.set(false);
          }
        },
        error: () => {
          this.articleError.set(
            'The help article could not be loaded. Please try again.',
          );
          this.articleLoading.set(false);
        },
      });
  }
}
