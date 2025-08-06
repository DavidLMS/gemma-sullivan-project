/**
 * Student Profile Types and Interfaces
 * Defines the core data structures for student information and validation.
 */

/**
 * Main student profile interface containing all essential information.
 * Used throughout the application for personalization and progress tracking.
 */
export interface StudentProfile {
  // Core Identity
  id: string              // 6-digit student ID (matches tutor-app format)
  name: string            // Full name
  
  // Academic Info
  age: number             // Student age
  grade: string           // Grade/course level
  language: string        // Preferred language (Spanish, English, etc.)
  
  // Personalization
  interests?: string      // Student interests (comma-separated)
  
  // System Data
  created_at: string      // Profile creation timestamp
  completedOnboarding: boolean
}

/** Current step in the student onboarding process */
export type OnboardingStep = 'welcome' | 'profile'

/** Status of profile synchronization with backend */
export type ProfileSyncStatus = 'pending' | 'synced' | 'error'

/** Status of registration with tutor app for teacher oversight */
export type TutorRegistrationStatus = 'none' | 'pending' | 'registered' | 'error'

/** Language option with localized display information */
export interface LanguageOption {
  code: string
  name: string
  nativeName: string
  flag: string
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
  { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹' }
]

// Grade level options
export const GRADE_LEVELS = [
  '6th grade',
  '7th grade', 
  '8th grade',
  '9th grade',
  '10th grade',
  '11th grade',
  '12th grade',
  'Other'
]

// Common interests suggestions
export const INTEREST_SUGGESTIONS = [
  'video games',
  'soccer',
  'basketball',
  'music',
  'art',
  'science',
  'reading',
  'cooking',
  'dance',
  'photography',
  'technology',
  'sports',
  'movies',
  'animals',
  'nature'
]

/**
 * Validates student ID format (must be exactly 6 digits).
 * @param id - Student ID to validate
 * @returns Validation result with error message if invalid
 */
export const validateStudentId = (id: string): { isValid: boolean; error?: string } => {
  if (!id) {
    return { isValid: false, error: 'Student ID is required' }
  }
  
  if (!/^\d{6}$/.test(id)) {
    return { isValid: false, error: 'Student ID must be exactly 6 digits' }
  }
  
  return { isValid: true }
}

/**
 * Validates student name (minimum 2 characters, required).
 * @param name - Student name to validate
 * @returns Validation result with error message if invalid
 */
export const validateName = (name: string): { isValid: boolean; error?: string } => {
  if (!name.trim()) {
    return { isValid: false, error: 'Name is required' }
  }
  
  if (name.trim().length < 2) {
    return { isValid: false, error: 'Name must be at least 2 characters' }
  }
  
  return { isValid: true }
}

/**
 * Validates student age (must be between 10-18 years).
 * @param age - Student age to validate
 * @returns Validation result with error message if invalid
 */
export const validateAge = (age: number): { isValid: boolean; error?: string } => {
  if (age < 10 || age > 18) {
    return { isValid: false, error: 'Age must be between 10 and 18' }
  }
  
  return { isValid: true }
}

/**
 * Find language option by ISO code.
 * @param code - ISO language code (e.g., 'en', 'es')
 * @returns Language option or undefined if not found
 */
export const getLanguageByCode = (code: string): LanguageOption | undefined => {
  return SUPPORTED_LANGUAGES.find(lang => lang.code === code)
}

/**
 * Get preferred language based on browser settings.
 * @returns Language name in English, defaults to 'English'
 */
export const getBrowserLanguage = (): string => {
  const browserLang = navigator.language.split('-')[0]
  const matchedLanguage = SUPPORTED_LANGUAGES.find(lang => lang.code === browserLang)
  return matchedLanguage ? matchedLanguage.name : 'English'
}

/**
 * Create empty profile with sensible defaults.
 * @returns Partial student profile ready for form initialization
 */
export const createEmptyProfile = (): Partial<StudentProfile> => ({
  id: '',
  name: '',
  age: 13,
  grade: '8th grade',
  language: getBrowserLanguage(),
  interests: '',
  completedOnboarding: false
})