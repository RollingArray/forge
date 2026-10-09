import { Component } from '@angular/core';

@Component({
  selector: 'app-login-shell',
  standalone: true,
  templateUrl: './login-shell.component.html',
  styleUrl: './login-shell.component.css',
})
export class LoginShellComponent {
  toggleTheme(): void {
    console.log('FORGE theme toggle');
  }
}
