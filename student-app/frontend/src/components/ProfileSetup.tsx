import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Check, AlertCircle, RefreshCw, X } from 'lucide-react'
import { 
  StudentProfile, 
  SUPPORTED_LANGUAGES, 
  GRADE_LEVELS, 
  INTEREST_SUGGESTIONS,
  validateStudentId,
  validateName,
  validateAge,
  createEmptyProfile
} from '../types/StudentProfile'
import { API_BASE } from '../config/api'

interface ProfileSetupProps {
  onComplete: (profile: StudentProfile) => void
  onBack: () => void
  initialProfile?: Partial<StudentProfile>
  isEditMode?: boolean
}


interface FormErrors {
  id?: string
  name?: string
  age?: string
  grade?: string
  language?: string
}

/**
 * ProfileSetup component handles student onboarding and profile editing.
 * Collects essential student information for personalized learning experience.
 * 
 * Features:
 * - Form validation with real-time feedback
 * - Support for both creation and editing modes
 * - Grade level and interest selection
 * - Language preference selection
 * 
 * @param props - Component props
 * @param props.onComplete - Callback when profile setup is completed
 * @param props.onBack - Callback to go back to previous step
 * @param props.initialProfile - Existing profile data for editing
 * @param props.isEditMode - Whether component is in edit mode
 */
const ProfileSetup = ({ onComplete, onBack, initialProfile, isEditMode = false }: ProfileSetupProps) => {
  // Generate random ID on first load
  const generateRandomId = () => {
    return Math.floor(100000 + Math.random() * 900000).toString()
  }
  
  const [profile, setProfile] = useState<Partial<StudentProfile>>(() => ({
    ...createEmptyProfile(),
    id: generateRandomId(), // Auto-generate ID
    ...initialProfile
  }))
  const [selectedInterests, setSelectedInterests] = useState<string[]>(() => {
    if (initialProfile?.interests) {
      return initialProfile.interests.split(', ').filter(i => i.trim())
    }
    return []
  })
  const [customInterest, setCustomInterest] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})





  const updateProfile = (field: keyof StudentProfile, value: any) => {
    setProfile(prev => ({ ...prev, [field]: value }))
    
    // Clear error for this field when user starts typing
    if (errors[field as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }

  }

  const handleGenerateNewId = () => {
    const newId = generateRandomId()
    updateProfile('id', newId)
  }

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    // In edit mode, skip ID and name validation
    if (!isEditMode) {
      // Validate Student ID
      const idValidation = validateStudentId(profile.id || '')
      if (!idValidation.isValid) {
        newErrors.id = idValidation.error
      }

      // Validate Name
      const nameValidation = validateName(profile.name || '')
      if (!nameValidation.isValid) {
        newErrors.name = nameValidation.error
      }
    }

    // Validate Age
    if (profile.age) {
      const ageValidation = validateAge(profile.age)
      if (!ageValidation.isValid) {
        newErrors.age = ageValidation.error
      }
    } else {
      newErrors.age = 'Age is required'
    }

    // Validate Grade
    if (!profile.grade) {
      newErrors.grade = 'Grade level is required'
    }
    
    // Validate Language
    if (!profile.language) {
      newErrors.language = 'Language is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }


  const handleComplete = () => {
    if (validateForm()) {
      const completeProfile: StudentProfile = {
        id: profile.id!,
        name: profile.name!,
        age: profile.age!,
        grade: profile.grade!,
        language: profile.language!,
        interests: selectedInterests.join(', '),
        created_at: new Date().toISOString(),
        completedOnboarding: true
      }
      
      // Profile completed
      
      onComplete(completeProfile)
    }
  }


  const toggleInterest = (interest: string) => {
    if (selectedInterests.includes(interest)) {
      setSelectedInterests(prev => prev.filter(i => i !== interest))
    } else {
      setSelectedInterests(prev => [...prev, interest])
    }
  }

  const addCustomInterest = () => {
    const trimmed = customInterest.trim()
    if (trimmed && !selectedInterests.includes(trimmed)) {
      setSelectedInterests(prev => [...prev, trimmed])
      setCustomInterest('')
    }
  }

  const removeInterest = (interest: string) => {
    setSelectedInterests(prev => prev.filter(i => i !== interest))
  }

  const handleCustomInterestKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addCustomInterest()
    }
  }

  return (
    <div className="bg-app-bg py-8 px-4">
      <div className="w-full max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">
            {isEditMode ? 'Edit Your Profile' : 'Set Up Your Profile'}
          </h1>
          <p className="text-gray-600">
            {isEditMode ? 'Update your information' : "Let's personalize your learning experience"}
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8 space-y-8">
          {/* Personal Information Section */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Personal Information</h2>
            <div className="space-y-6">
              {/* Student ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Student ID <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      value={profile.id || ''}
                      onChange={(e) => {
                        if (!isEditMode) {
                          const value = e.target.value.replace(/\D/g, '').slice(0, 6)
                          updateProfile('id', value)
                        }
                      }}
                      placeholder="123456"
                      maxLength={6}
                      disabled={isEditMode}
                      className={`w-full px-4 py-3 rounded-xl border focus:ring-2 focus:ring-primary/20 focus:outline-none transition-all ${
                        isEditMode 
                          ? 'bg-gray-100 text-gray-500 cursor-not-allowed' 
                          : errors.id 
                          ? 'bg-gray-50 focus:bg-white border-red-300 focus:border-red-500' 
                          : 'bg-gray-50 focus:bg-white border-gray-300 focus:border-primary'
                      }`}
                    />
                  </div>
                  {!isEditMode && (
                    <button
                      onClick={handleGenerateNewId}
                      className="px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition-colors flex items-center"
                      title="Generate new ID"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  )}
                </div>
                {errors.id && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.id}
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Your 6-digit student ID (auto-generated)
                </p>
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={profile.name || ''}
                  onChange={(e) => {
                    if (!isEditMode) {
                      updateProfile('name', e.target.value)
                    }
                  }}
                  placeholder="Enter your name"
                  disabled={isEditMode}
                  className={`w-full px-4 py-3 rounded-xl border focus:ring-2 focus:ring-primary/20 focus:outline-none transition-all ${
                    isEditMode 
                      ? 'bg-gray-100 text-gray-500 cursor-not-allowed' 
                      : errors.name 
                      ? 'bg-gray-50 focus:bg-white border-red-300 focus:border-red-500' 
                      : 'bg-gray-50 focus:bg-white border-gray-300 focus:border-primary'
                  }`}
                />
                {errors.name && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.name}
                  </div>
                )}
              </div>

              {/* Age */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Age <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={profile.age || ''}
                  onChange={(e) => updateProfile('age', parseInt(e.target.value) || 0)}
                  placeholder="Enter your age"
                  min="1"
                  max="100"
                  className={`w-full px-4 py-3 rounded-xl border bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary/20 focus:outline-none transition-all ${
                    errors.age ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-primary'
                  }`}
                />
                {errors.age && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.age}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Academic Details Section */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Academic Details</h2>
            <div className="space-y-6">
              {/* Grade Level */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Grade Level <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={profile.grade || ''}
                  onChange={(e) => updateProfile('grade', e.target.value)}
                  placeholder="Enter your grade level (e.g., 9th grade, High School, etc.)"
                  className={`w-full px-4 py-3 rounded-xl border bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary/20 focus:outline-none transition-all ${
                    errors.grade ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-primary'
                  }`}
                />
                {errors.grade && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.grade}
                  </div>
                )}
              </div>

              {/* Language */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Preferred Language <span className="text-red-500">*</span>
                </label>
                <select
                  value={profile.language || ''}
                  onChange={(e) => updateProfile('language', e.target.value)}
                  className={`w-full px-4 py-3 rounded-xl border bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary/20 focus:outline-none transition-all ${
                    errors.language ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-primary'
                  }`}
                >
                  <option value="">Select your preferred language</option>
                  {SUPPORTED_LANGUAGES.map(lang => (
                    <option key={lang.code} value={lang.name}>
                      {lang.nativeName} ({lang.name})
                    </option>
                  ))}
                </select>
                {errors.language && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.language}
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Content and questions will be generated in this language
                </p>
              </div>
            </div>
          </div>

          {/* Interests & Personalization Section */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Interests & Personalization</h2>
            <div className="space-y-6">
              {/* Selected Interests */}
              {selectedInterests.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-3">Your interests:</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedInterests.map(interest => (
                      <span
                        key={interest}
                        className="inline-flex items-center px-3 py-1 text-sm bg-primary-50 text-primary-dark border border-primary-200 rounded-full"
                      >
                        {interest}
                        <button
                          onClick={() => removeInterest(interest)}
                          className="ml-2 text-primary-dark hover:text-red-600 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Interest Suggestions */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-3">Select your interests:</p>
                <div className="flex flex-wrap gap-2">
                  {INTEREST_SUGGESTIONS.map(interest => (
                    <button
                      key={interest}
                      onClick={() => toggleInterest(interest)}
                      className={`px-3 py-2 text-sm border rounded-full transition-all duration-200 ${
                        selectedInterests.includes(interest)
                          ? 'bg-primary text-white border-primary'
                          : 'bg-gray-100 hover:bg-primary-50 hover:text-primary-dark border-gray-200 hover:border-primary-200'
                      }`}
                    >
                      {interest}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Interest Input */}
              <div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customInterest}
                    onChange={(e) => setCustomInterest(e.target.value)}
                    onKeyPress={handleCustomInterestKeyPress}
                    placeholder="Enter a custom interest..."
                    className="flex-1 px-4 py-2 rounded-xl border border-gray-300 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary focus:outline-none transition-all"
                  />
                  <button
                    onClick={addCustomInterest}
                    disabled={!customInterest.trim()}
                    className="px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Add
                  </button>
                </div>
              </div>

            </div>
          </div>


          {/* Action Buttons */}
          <div className="pt-6 border-t border-gray-200">
            {isEditMode ? (
              <div className="flex gap-3">
                <button
                  onClick={onBack}
                  className="flex-1 flex items-center justify-center px-6 py-4 border border-gray-300 text-gray-700 font-semibold rounded-xl transition-all duration-300 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleComplete}
                  className="flex-1 flex items-center justify-center px-6 py-4 bg-gradient-to-r from-primary to-primary-dark hover:from-primary-dark hover:to-gray-800 text-white font-semibold rounded-xl transition-all duration-300 shadow-md hover:shadow-lg hover:-translate-y-0.5"
                >
                  <span>Save Changes</span>
                  <Check className="w-5 h-5 ml-2" />
                </button>
              </div>
            ) : (
              <button
                onClick={handleComplete}
                className="w-full flex items-center justify-center px-6 py-4 bg-gradient-to-r from-primary to-primary-dark hover:from-primary-dark hover:to-gray-800 text-white font-semibold rounded-xl transition-all duration-300 shadow-md hover:shadow-lg hover:-translate-y-0.5"
              >
                <span>Complete Setup</span>
                <Check className="w-5 h-5 ml-2" />
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}

export default ProfileSetup