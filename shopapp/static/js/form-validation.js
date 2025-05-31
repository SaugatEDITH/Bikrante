// Minimal, non-conflicting validation for signup and profile forms

document.addEventListener("DOMContentLoaded", function () {
  // Signup form validation
  const signupForm = document.querySelector('form[action*="signup"]');
  if (signupForm) {
    const username = signupForm.querySelector('input[name="username"]');
    const email = signupForm.querySelector('input[name="email"]');
    const password = signupForm.querySelector('input[name="password"]');
    const cpassword = signupForm.querySelector('input[name="cpassword"]');

    if (username) {
      username.addEventListener("blur", function () {
        if (username.value.length < 3) {
          username.setCustomValidity("Username must be at least 3 characters.");
          username.style.borderColor = "red";
        } else {
          username.setCustomValidity("");
          username.style.borderColor = "";
        }
      });
    }

    if (email) {
      email.addEventListener("blur", function () {
        // Email must start with a letter, then normal email pattern
        // Not starting with number or special char
        const re = /^[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
        if (!re.test(email.value)) {
          email.setCustomValidity("Email must start with a letter and be valid.");
          // Optionally show a message in the backend message div if present
          const msgDiv = signupForm.querySelector('.alert');
          if (msgDiv) {
            msgDiv.textContent = "Email must start with a letter and be valid.";
            msgDiv.style.color = "red";
          }
          email.style.borderColor = "red";
        } else {
          email.setCustomValidity("");
          email.style.borderColor = "";
        }
      });
    }

    if (password && cpassword) {
      password.addEventListener("blur", function () {
        // Password must have at least 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
        const pwRe = /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$/;
        if (!pwRe.test(password.value)) {
          password.setCustomValidity("Password must be at least 8 characters and include uppercase, lowercase, number, and special character.");
          password.style.borderColor = "red";
        } else {
          password.setCustomValidity("");
          password.style.borderColor = "";
        }
      });

      cpassword.addEventListener("blur", function () {
        if (cpassword.value !== password.value) {
          cpassword.setCustomValidity("Passwords do not match.");
          cpassword.style.borderColor = "red";
        } else {
          cpassword.setCustomValidity("");
          cpassword.style.borderColor = "";
        }
      });
    }
  }

  // Profile setup and update profile validation
  const profileForms = [
    document.querySelector('#profile-setup-form'),
    document.querySelector('#update-profile-form')
  ];

  profileForms.forEach(form => {
    if (form) {
      const username = form.querySelector('input[name="username"]');
      const address = form.querySelector('textarea[name="address"]');
      const phone = form.querySelector('input[name="phone_number"]');
      const profileImage = form.querySelector('input[name="profile_image"]');

      if (username) {
        username.addEventListener("blur", function () {
          if (username.value.trim().length < 3) {
            username.setCustomValidity("Username must be at least 3 characters.");
            username.style.borderColor = "red";
          } else {
            username.setCustomValidity("");
            username.style.borderColor = "";
          }
        });
      }

      if (address) {
        address.addEventListener("blur", function () {
          if (address.value.trim().length <= 3) {
        address.setCustomValidity("Address must be more than 3 characters.");
        address.style.borderColor = "red";
          } else {
        address.setCustomValidity("");
        address.style.borderColor = "";
          }
        });
      }

      if (phone) {
        phone.addEventListener("blur", function () {
          const mobileRegex = /^(97|98)\d{7,8}$/;
          const landlineRegex = /^(01|04|05|06|07)\d{6,7}$/;
          if (!phone.value.trim() || !(mobileRegex.test(phone.value) || landlineRegex.test(phone.value))) {
            phone.setCustomValidity("Enter a valid Nepali phone number.");
            phone.style.borderColor = "red";
          } else {
            phone.setCustomValidity("");
            phone.style.borderColor = "";
          }
        });
      }

      if (profileImage) {
        profileImage.addEventListener("change", function () {
          const allowedExtensions = ['jpeg', 'png', 'jpg'];
          const fileExtension = profileImage.value.split('.').pop().toLowerCase();
          if (!allowedExtensions.includes(fileExtension)) {
            profileImage.setCustomValidity("Only JPEG, PNG, and JPG image formats are allowed.");
            profileImage.style.borderColor = "red";
          } else {
            profileImage.setCustomValidity("");
            profileImage.style.borderColor = "";
          }
        });
      }
    }
  });

  // Change password validation (if present)
  const changePasswordForm = document.querySelector('form[action*="change_password"], form[action*="change-password"]');
  if (changePasswordForm) {
    const newPassword = changePasswordForm.querySelector('input[name="new_password"]');
    const confirmPassword = changePasswordForm.querySelector('input[name="confirm_password"]');
    if (newPassword && confirmPassword) {
      newPassword.addEventListener("blur", function () {
        if (newPassword.value.length < 8) {
          newPassword.setCustomValidity("Password must be at least 8 characters.");
          newPassword.style.borderColor = "red";
        } else {
          newPassword.setCustomValidity("");
          newPassword.style.borderColor = "";
        }
      });
      confirmPassword.addEventListener("blur", function () {
        if (confirmPassword.value !== newPassword.value) {
          confirmPassword.setCustomValidity("Passwords do not match.");
          confirmPassword.style.borderColor = "red";
        } else {
          confirmPassword.setCustomValidity("");
          confirmPassword.style.borderColor = "";
        }
      });
    }
  }

  // Change password validation for user-dashboard
  const changePasswordFormDashboard = document.querySelector('#change-password-form');
  if (changePasswordFormDashboard) {
    const currentPassword = changePasswordFormDashboard.querySelector('input[name="current_password"]');
    const newPassword = changePasswordFormDashboard.querySelector('input[name="new_password"]');
    const confirmPassword = changePasswordFormDashboard.querySelector('input[name="confirm_password"]');

    if (currentPassword) {
      currentPassword.addEventListener("blur", function () {
        if (currentPassword.value.trim().length === 0) {
          currentPassword.setCustomValidity("Current password is required.");
          currentPassword.style.borderColor = "red";
        } else {
          currentPassword.setCustomValidity("");
          currentPassword.style.borderColor = "";
        }
      });
    }

    if (newPassword) {
      newPassword.addEventListener("blur", function () {
        const pwRe = /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$/;
        if (!pwRe.test(newPassword.value)) {
          newPassword.setCustomValidity("Password must be at least 8 characters and include uppercase, lowercase, number, and special character.");
          newPassword.style.borderColor = "red";
        } else {
          newPassword.setCustomValidity("");
          newPassword.style.borderColor = "";
        }
      });
    }

    if (confirmPassword) {
      confirmPassword.addEventListener("blur", function () {
        if (confirmPassword.value !== newPassword.value) {
          confirmPassword.setCustomValidity("Passwords do not match.");
          confirmPassword.style.borderColor = "red";
        } else {
          confirmPassword.setCustomValidity("");
          confirmPassword.style.borderColor = "";
        }
      });
    }
  }

  // Contact form validation
  const contactForm = document.querySelector('form.contact__form');
  if (contactForm) {
    // Use querySelector with [name] attribute to ensure correct selection
    const name = contactForm.querySelector('input[name="name"], #name');
    const email = contactForm.querySelector('input[name="email"], #email');
    const subject = contactForm.querySelector('input[name="subject"], #subject');
    const message = contactForm.querySelector('textarea[name="message"], #message');

    if (name) {
      name.addEventListener("blur", function () {
        if (name.value.trim().length <=3) {
          name.setCustomValidity("Name must be at least 3 characters.");
          name.style.borderColor = "red";
        } else {
          name.setCustomValidity("");
          name.style.borderColor = "";
        }
      });
    }

    if (email) {
      email.addEventListener("blur", function () {
        const re = /^[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
        if (!re.test(email.value)) {
          email.setCustomValidity("Email must start with a letter and be valid.");
          email.style.borderColor = "red";
        } else {
          email.setCustomValidity("");
          email.style.borderColor = "";
        }
      });
    }

    if (subject) {
      subject.addEventListener("blur", function () {
        if (subject.value.trim().length <= 3) {
          subject.setCustomValidity("Subject must be at least 3 characters.");
          subject.style.borderColor = "red";
        } else {
          subject.setCustomValidity("");
          subject.style.borderColor = "";
        }
      });
    }

    if (message) {
      message.addEventListener("blur", function () {
        if (message.value.trim().length < 10) {
          message.setCustomValidity("Message must be at least 10 characters.");
          message.style.borderColor = "red";
        } else {
          message.setCustomValidity("");
          message.style.borderColor = "";
        }
      });
    }
  }
});
