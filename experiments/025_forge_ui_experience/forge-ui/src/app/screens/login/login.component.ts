import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  readonly email = signal('');

  constructor(private readonly router: Router) {}

  continue(): void {
    const value = this.email().trim();

    if (!value) {
      return;
    }

    console.log('FORGE login:', value);
    this.router.navigate(['/home']);
  }

  continueWithMicrosoft(): void {
    console.log('FORGE Microsoft authentication');
  }

  toggleTheme(): void {
    console.log('FORGE theme toggle');
  }
}
