import { useState, useEffect, useRef, useCallback } from 'react'
import { WifiOff, Wifi, Check } from 'lucide-react'
import MainMenu from './components/MainMenu'
import Learn from './components/Learn'
import Practice from './components/Practice'
import Experiment from './components/Experiment'
import Discover from './components/Discover'
import Welcome from './components/Welcome'
import ProfileSetup from './components/ProfileSetup'
import { StudentProfile, OnboardingStep, ProfileSyncStatus, TutorRegistrationStatus } from './types/StudentProfile'
import { API_BASE } from './config/api'

/**
 * Main application component that manages student onboarding, profile management, and navigation.
 * Handles real-time synchronization with tutor app via SSE and provides central navigation hub.
 * 
 * Features:
 * - Student profile onboarding flow
 * - Real-time sync status with tutor app
 * - SSE-based notifications for content updates
 * - Debounced sync operations
 * - Conditional rendering based on onboarding completion
 * 
 * @returns The main App component with conditional rendering
 */
function App() {
  // Student profile and onboarding state
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(null)
  const [isOnboardingComplete, setIsOnboardingComplete] = useState<boolean>(false)
  const [onboardingStep, setOnboardingStep] = useState<OnboardingStep>('welcome')
  const [profileSyncStatus, setProfileSyncStatus] = useState<ProfileSyncStatus>('pending')
  const [tutorRegistrationStatus, setTutorRegistrationStatus] = useState<TutorRegistrationStatus>('none')
  
  // App navigation state
  const [isSyncAvailable, setIsSyncAvailable] = useState<boolean>(false)
  const [isSyncing, setIsSyncing] = useState<boolean>(false)
  const [currentView, setCurrentView] = useState<'menu' | 'learn' | 'practice' | 'experiment' | 'discover' | 'profile'>('menu')
  const [isEditingProfile, setIsEditingProfile] = useState<boolean>(false)
  
  // Debounce refs
  const syncTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const syncDebounceTime = 3000 // 3 seconds

  // Load student profile from backend
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/profile/current`)
        if (response.ok) {
          const data = await response.json()
          if (data.success && data.profile) {
            const profile: StudentProfile = data.profile
            setStudentProfile(profile)
            setIsOnboardingComplete(true)
            setProfileSyncStatus('synced')
          } else {
            // No profile found, start onboarding
            setOnboardingStep('welcome')
          }
        } else {
          // Backend not available, start onboarding
          setOnboardingStep('welcome')
        }
      } catch (error) {
        // Could not load profile from backend
        setOnboardingStep('welcome')
      }
    }
    
    loadProfile()
    
    // Check for tutor service availability
    checkTutorService()
    
    // Set up periodic check for tutor service (fallback)
    const interval = setInterval(checkTutorService, 30000) // Check every 30 seconds
    
    return () => {
      clearInterval(interval)
      // Cleanup debounce timeout
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
      }
    }
  }, [])

  // SSE: Listen for real-time sync and content updates
  useEffect(() => {
    const eventSource = new EventSource('/api/events/stream')
    
    eventSource.onopen = () => {
      // SSE connection opened for sync updates
    }
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // SSE event received
        
        // Handle different event types
        switch (data.type) {
          case 'connected':
            // SSE connected successfully
            break
            
          case 'heartbeat':
            // Heartbeat to keep connection alive - no action needed
            break
            
          case 'tutor_sync_enabled':
            // Tutor sync enabled - updating icon
            setIsSyncAvailable(true)
            break
            
          case 'tutor_sync_disabled':
            // Tutor sync disabled - updating icon
            setIsSyncAvailable(false)
            break
            
          case 'content_added':
          case 'processing_started':
          case 'processing_completed':
          case 'processing_failed':
            // These events are handled by individual components
            // Content event processed
            break
            
          default:
            // Unknown SSE event type
        }
      } catch (error) {
        // Error parsing SSE event
      }
    }
    
    eventSource.onerror = (error) => {
      // SSE connection error
    }
    
    // Cleanup on unmount
    return () => {
      // SSE connection closed
      eventSource.close()
    }
  }, [])

  /**
   * Check if tutor service is available for synchronization.
   * Updates sync availability state based on response.
   */
  const checkTutorService = async () => {
    try {
      // Checking tutor service availability
      const response = await fetch('/api/sync/check-tutor')
      
      // Response details logged
      
      if (response.ok) {
        // Check Content-Type before parsing
        const contentType = response.headers.get('content-type')
        // Content-Type checked
        
        if (contentType && contentType.includes('application/json')) {
          try {
            const data = await response.json()
            // Tutor service check response
            setIsSyncAvailable(data.available)
            
            // Tutor service availability checked
          } catch (jsonError) {
            // JSON parsing error
            const rawText = await response.text()
            // Raw response logged
            setIsSyncAvailable(false)
          }
        } else {
          // Response is not JSON
          const rawText = await response.text()
          // Raw response logged
          setIsSyncAvailable(false)
        }
      } else {
        // Tutor service check failed
        const errorText = await response.text()
        // Error details logged
        setIsSyncAvailable(false)
      }
    } catch (error) {
      // Error checking tutor service
      setIsSyncAvailable(false)
    }
  }

  /**
   * Perform synchronization with tutor app.
   * Includes minimum duration for better UX and handles errors gracefully.
   */
  const performSync = useCallback(async () => {
    if (!isSyncAvailable) return
    
    // Starting sync to tutor
    // Note: setIsSyncing(true) already called in handleSync for immediate feedback
    
    const syncStartTime = Date.now()
    const minimumSyncDuration = 5000 // 5 seconds minimum
    
    try {
      const response = await fetch('/api/sync/to-tutor', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const result = await response.json()
        // Sync completed successfully
        if (result.assigned_content?.length > 0) {
          // New content assigned
        }
        if (result.removed_content?.length > 0) {
          // Content removed
        }
      } else {
        const errorText = await response.text()
        // Sync failed
      }
    } catch (error) {
      // Sync error
    }
    
    // Ensure minimum sync duration for better UX
    const syncDuration = Date.now() - syncStartTime
    const remainingTime = Math.max(0, minimumSyncDuration - syncDuration)
    
    setTimeout(() => {
      setIsSyncing(false)
      // Sync process finished
    }, remainingTime)
    
  }, [isSyncAvailable, isSyncing])

  /**
   * Handle sync button click with debouncing.
   * Prevents multiple rapid sync requests.
   */
  const handleSync = useCallback(() => {
    // Clear any existing timeout
    if (syncTimeoutRef.current) {
      clearTimeout(syncTimeoutRef.current)
    }
    
    // Show spinner immediately
    setIsSyncing(true)
    // Sync queued
    
    // Set debounced sync
    syncTimeoutRef.current = setTimeout(() => {
      performSync()
    }, syncDebounceTime)
  }, [performSync, syncDebounceTime])


  const handleNavigation = (view: 'menu' | 'learn' | 'practice' | 'experiment' | 'discover' | 'profile') => {
    setCurrentView(view)
  }

  const handleEditProfile = () => {
    setIsEditingProfile(true)
    setCurrentView('profile')
  }

  const handleProfileEditComplete = async (updatedProfile: StudentProfile) => {
    // Keep original ID and name
    const finalProfile = {
      ...updatedProfile,
      id: studentProfile!.id,
      name: studentProfile!.name
    }
    
    setStudentProfile(finalProfile)
    
    // Save to backend
    await saveProfileToBackend(finalProfile)
    
    // Return to menu
    setIsEditingProfile(false)
    setCurrentView('menu')
  }

  const handleCancelProfileEdit = () => {
    setIsEditingProfile(false)
    setCurrentView('menu')
  }

  // Profile management functions
  const saveProfileToBackend = async (profile: StudentProfile) => {
    try {
      setProfileSyncStatus('pending')
      
      const response = await fetch(`${API_BASE}/api/profile/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ profile })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setProfileSyncStatus('synced')
          // Profile saved to backend successfully
        } else {
          setProfileSyncStatus('error')
          // Backend profile save failed
        }
      } else {
        setProfileSyncStatus('error')
        // Profile save request failed
      }
    } catch (error) {
      setProfileSyncStatus('error')
      // Error saving profile to backend
    }
  }

  const handleWelcomeGetStarted = () => {
    setOnboardingStep('profile')
  }

  const handleProfileSetupComplete = async (profile: StudentProfile) => {
    try {
      // Save to backend
      await saveProfileToBackend(profile)
      
      // Update app state and complete onboarding immediately
      setStudentProfile(profile)
      setIsOnboardingComplete(true)
      
      // Try to register with tutor-app (non-blocking)
      try {
        const response = await fetch(`${API_BASE}/api/profile/register-with-tutor`, {
          method: 'POST'
        })
        
        if (response.ok) {
          const data = await response.json()
          if (data.success) {
            setTutorRegistrationStatus('registered')
            // Registered with tutor-app successfully
          } else {
            setTutorRegistrationStatus('error')
            // Failed to register with tutor-app
          }
        }
      } catch (error) {
        setTutorRegistrationStatus('error')
        // Could not register with tutor-app
      }
      
    } catch (error) {
      // Error completing profile setup
    }
  }

  const handleBackToWelcome = () => {
    setOnboardingStep('welcome')
  }

  // Show onboarding if not complete
  if (!isOnboardingComplete) {
    return (
      <div className={`relative w-full h-screen ${onboardingStep === 'profile' ? 'overflow-y-auto' : 'overflow-hidden'}`}>
        {/* Welcome Screen */}
        <div className={`absolute inset-0 transition-all duration-500 ease-out ${
          onboardingStep === 'welcome' 
            ? 'translate-x-0 opacity-100 z-20' 
            : onboardingStep === 'profile'
            ? '-translate-x-full opacity-0 z-10'
            : '-translate-x-full opacity-0 z-0'
        }`}>
          <Welcome onGetStarted={handleWelcomeGetStarted} />
        </div>

        {/* Profile Setup Screen */}
        <div className={`${onboardingStep === 'profile' ? 'relative w-full min-h-screen' : 'absolute inset-0'} transition-all duration-500 ease-out ${
          onboardingStep === 'profile' 
            ? 'translate-x-0 opacity-100 z-20' 
            : onboardingStep === 'welcome'
            ? 'translate-x-full opacity-0 z-10'
            : 'translate-x-full opacity-0 z-0'
        }`}>
          <ProfileSetup
            onComplete={handleProfileSetupComplete}
            onBack={handleBackToWelcome}
            initialProfile={studentProfile || undefined}
          />
        </div>

      </div>
    )
  }

  // Show main app if onboarding is complete
  return (
    <div className="min-h-screen bg-app-bg">
      
      {/* Header - only show for menu view */}
      {currentView === 'menu' && (
        <header className="flex justify-between items-center p-4 bg-card-bg shadow-sm">
          {/* Greeting with logo */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <img 
                src="/logo.svg" 
                alt="Gemma Logo" 
                className="w-8 h-8 object-contain"
              />
            </div>
            <div className="text-lg font-medium text-gray-800">
              Hello, <button 
                onClick={handleEditProfile}
                className="text-gray-800 hover:text-primary transition-colors"
              >
                {studentProfile?.name || 'Student'}
              </button>!
            </div>
          </div>

          {/* Sync button */}
          <button 
            onClick={isSyncAvailable ? handleSync : undefined}
            className={`p-2 rounded-lg border transition-all duration-300 ${
              isSyncAvailable
                ? isSyncing
                  ? 'border-blue-300 bg-blue-50 cursor-wait'
                  : 'border-green-300 bg-green-50 hover:bg-green-100 cursor-pointer'
                : 'border-gray-300 bg-gray-50 opacity-50 cursor-not-allowed'
            }`}
            disabled={!isSyncAvailable || isSyncing}
            title={
              isSyncing
                ? 'Syncing with tutor...'
                : isSyncAvailable
                ? 'Sync with tutor - click to sync (debounced 3s)'
                : 'No tutor connection available'
            }
          >
            {isSyncing ? (
              <WifiOff className="w-5 h-5 text-blue-500 animate-spin" />
            ) : isSyncAvailable ? (
              <Wifi className="w-5 h-5 text-green-600" />
            ) : (
              <WifiOff className="w-5 h-5 text-gray-400" />
            )}
          </button>
        </header>
      )}

      {/* All components stay mounted, visibility controlled by CSS */}
      <div className="flex-1">
        {/* Main Menu */}
        <div style={{ display: currentView === 'menu' ? 'block' : 'none' }}>
          <MainMenu onNavigate={handleNavigation} />
        </div>

        {/* Learn Component - stays mounted */}
        <div style={{ display: currentView === 'learn' ? 'block' : 'none' }}>
          <Learn onBack={() => setCurrentView('menu')} />
        </div>

        {/* Practice Component */}
        <div style={{ display: currentView === 'practice' ? 'block' : 'none' }}>
          <Practice onBack={() => setCurrentView('menu')} onNavigate={handleNavigation} />
        </div>

        {/* Experiment Component */}
        <div style={{ display: currentView === 'experiment' ? 'block' : 'none' }}>
          <Experiment onBack={() => setCurrentView('menu')} onNavigate={handleNavigation} />
        </div>

        {/* Discover Component */}
        <div style={{ display: currentView === 'discover' ? 'block' : 'none' }}>
          <Discover onBack={() => setCurrentView('menu')} />
        </div>

        {/* Profile Edit Component */}
        <div style={{ display: currentView === 'profile' ? 'block' : 'none' }}>
          {isEditingProfile && studentProfile && (
            <ProfileSetup
              onComplete={handleProfileEditComplete}
              onBack={handleCancelProfileEdit}
              initialProfile={studentProfile}
              isEditMode={true}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default App