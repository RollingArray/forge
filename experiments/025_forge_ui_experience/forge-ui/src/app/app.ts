import { Component } from '@angular/core';
import { LoginComponent } from './screens/login/login.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LoginComponent],
  template: '<app-login />',
})
export class App {
}
