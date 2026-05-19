'use client'

import type React from 'react'

import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  PlayIcon,
  PauseIcon,
  SettingsIcon,
  CheckCircleIcon,
  FolderOpenIcon,
  SparklesIcon,
  FileIcon,
  ImageIcon,
  VideoIcon,
  MusicIcon,
  CodeIcon,
  ArchiveIcon,
  FileTextIcon,
  AlertTriangleIcon,
  PlusIcon,
  SearchIcon,
} from 'lucide-react'

interface DetectedFileType {
  extension: string
  count: number
  defaultFolder: string
  customFolder?: string
  color: string
  icon: React.ReactNode
  enabled: boolean
  isUnmapped?: boolean
}

const sampleDetectedFiles: DetectedFileType[] = [
  {
    extension: 'jpg',
    count: 45,
    defaultFolder: 'Images',
    color: 'text-pink-500',
    icon: <ImageIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'png',
    count: 32,
    defaultFolder: 'Images',
    color: 'text-pink-500',
    icon: <ImageIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'pdf',
    count: 23,
    defaultFolder: 'Documents',
    color: 'text-red-500',
    icon: <FileTextIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'docx',
    count: 18,
    defaultFolder: 'Documents',
    color: 'text-blue-500',
    icon: <FileIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'mp4',
    count: 12,
    defaultFolder: 'Videos',
    color: 'text-purple-500',
    icon: <VideoIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'mp3',
    count: 8,
    defaultFolder: 'Music',
    color: 'text-green-500',
    icon: <MusicIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'js',
    count: 15,
    defaultFolder: 'Code',
    color: 'text-yellow-500',
    icon: <CodeIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'zip',
    count: 6,
    defaultFolder: 'Archives',
    color: 'text-orange-500',
    icon: <ArchiveIcon className="h-4 w-4" />,
    enabled: true,
  },
  {
    extension: 'sketch',
    count: 4,
    defaultFolder: 'Unmapped',
    color: 'text-gray-500',
    icon: <AlertTriangleIcon className="h-4 w-4" />,
    enabled: false,
    isUnmapped: true,
  },
  {
    extension: 'psd',
    count: 7,
    defaultFolder: 'Unmapped',
    color: 'text-gray-500',
    icon: <AlertTriangleIcon className="h-4 w-4" />,
    enabled: false,
    isUnmapped: true,
  },
  {
    extension: 'ai',
    count: 3,
    defaultFolder: 'Unmapped',
    color: 'text-gray-500',
    icon: <AlertTriangleIcon className="h-4 w-4" />,
    enabled: false,
    isUnmapped: true,
  },
]

export function FileOrganizerInterface() {
  const [sourceFolder, setSourceFolder] = useState('/Users/john/Downloads')
  const [destinationFolder, setDestinationFolder] = useState('/Users/john/Organized')
  const [isRunning, setIsRunning] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [hasScanned, setHasScanned] = useState(false) // Reset to false for proper initial state
  const [progress, setProgress] = useState(0)
  const [processedFiles, setProcessedFiles] = useState(0)
  const [totalFiles, setTotalFiles] = useState(0) // Reset to 0 for proper initial state

  const [detectedFileTypes, setDetectedFileTypes] = useState<DetectedFileType[]>([]) // Start with empty array
  const settingsRef = useRef<HTMLDivElement>(null) // Add ref for scrolling to settings section

  const handleScanFiles = () => {
    if (!sourceFolder) return

    setIsScanning(true)
    setTotalFiles(0)

    const scanInterval = setInterval(() => {
      setTotalFiles((prev) => {
        const newTotal = prev + Math.floor(Math.random() * 10) + 1
        if (newTotal >= 177) {
          clearInterval(scanInterval)
          setIsScanning(false)
          setTotalFiles(177)
          setHasScanned(true) // Mark scan as completed
          setDetectedFileTypes(sampleDetectedFiles) // Populate with found files

          setTimeout(() => {
            settingsRef.current?.scrollIntoView({
              behavior: 'smooth',
              block: 'start',
            })
          }, 500)

          return 177
        }
        return newTotal
      })
    }, 200)
  }

  const handleStartOrganization = () => {
    if (!sourceFolder || !destinationFolder) return

    setIsRunning(true)
    setProgress(0)
    setProcessedFiles(0)
    const enabledFiles = detectedFileTypes
      .filter((ft) => ft.enabled)
      .reduce((sum, ft) => sum + ft.count, 0)
    setTotalFiles(enabledFiles)

    const interval = setInterval(() => {
      setProgress((prev) => {
        const newProgress = prev + Math.random() * 8
        setProcessedFiles(Math.floor((newProgress / 100) * enabledFiles))

        if (newProgress >= 100) {
          clearInterval(interval)
          setIsRunning(false)
          setProgress(100)
          setProcessedFiles(enabledFiles)
          return 100
        }
        return newProgress
      })
    }, 300)
  }

  const updateCustomFolder = (extension: string, newFolder: string) => {
    setDetectedFileTypes((prev) =>
      prev.map((ft) => (ft.extension === extension ? { ...ft, customFolder: newFolder } : ft))
    )
  }

  const toggleExtension = (extension: string) => {
    setDetectedFileTypes((prev) =>
      prev.map((ft) => (ft.extension === extension ? { ...ft, enabled: !ft.enabled } : ft))
    )
  }

  const enabledExtensions = detectedFileTypes.filter((ft) => ft.enabled)
  const unmappedExtensions = detectedFileTypes.filter((ft) => ft.isUnmapped)
  const totalEnabledFiles = enabledExtensions.reduce((sum, ft) => sum + ft.count, 0)

  return (
    <div className="fun-background min-h-screen">
      <div className="container mx-auto max-w-7xl px-6 py-8">
        <div className="mb-1 text-center">
          <div className="gradient-primary mb-4 inline-flex items-center gap-2 rounded-2xl p-6 py-8">
            <SparklesIcon className="h-10 w-10 text-black" />
            <div className="text-center">
              <h1 className="text-4xl font-bold text-balance text-black">File Organizer</h1>
              <p className="text-lg text-pretty text-black/80">
                Transform chaos into order with intelligent file sorting
              </p>
            </div>
          </div>
        </div>

        <div className="mb-8">
          <Card className="border-primary/20 shadow-primary/10 border-2 bg-white/90 shadow-2xl backdrop-blur-md">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-3 text-2xl text-gray-900">
                <div className="gradient-primary rounded-xl p-2">
                  <FolderOpenIcon className="text-primary-foreground h-6 w-6" />
                </div>
                Folder Organization
              </CardTitle>
              <CardDescription className="text-lg text-gray-700">
                Select your source and destination folders to begin organizing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <div className="space-y-3">
                  <Label htmlFor="source" className="text-base font-medium text-gray-800">
                    Source Folder
                  </Label>
                  <div className="flex gap-3">
                    <Input
                      id="source"
                      placeholder="/path/to/messy/folder"
                      value={sourceFolder}
                      onChange={(e) => setSourceFolder(e.target.value)}
                      className="focus:border-primary/50 h-12 border-2 font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="lg"
                      className="hover:border-primary/40 transform border-gray-300 bg-white/80 px-6 text-gray-800 transition-all duration-300 hover:scale-105 hover:bg-gradient-to-r hover:from-blue-50 hover:to-green-50 hover:text-gray-900 hover:shadow-md"
                    >
                      Browse
                    </Button>
                  </div>
                </div>
                <div className="space-y-3">
                  <Label htmlFor="destination" className="text-base font-medium text-gray-800">
                    Destination Folder
                  </Label>
                  <div className="flex gap-3">
                    <Input
                      id="destination"
                      placeholder="/path/to/organized/folder"
                      value={destinationFolder}
                      onChange={(e) => setDestinationFolder(e.target.value)}
                      className="focus:border-primary/50 h-12 border-2 font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="lg"
                      className="hover:border-primary/40 transform border-gray-300 bg-white/80 px-6 text-gray-800 transition-all duration-300 hover:scale-105 hover:bg-gradient-to-r hover:from-blue-50 hover:to-green-50 hover:text-gray-900 hover:shadow-md"
                    >
                      Browse
                    </Button>
                  </div>
                </div>
              </div>

              {isScanning && (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-4 w-4 animate-pulse rounded-full bg-blue-500" />
                    <span className="font-medium text-blue-800">Scanning folder for files...</span>
                    <span className="text-blue-600">{totalFiles} files found so far</span>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-center pt-4">
                <div className="flex items-center gap-4">
                  <Button
                    onClick={handleScanFiles}
                    disabled={isScanning || !sourceFolder}
                    size="lg"
                    className="gradient-primary transform px-8 py-6 text-xl font-bold text-black shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:brightness-110"
                  >
                    <SearchIcon className="mr-2 h-5 w-5" />
                    {isScanning ? 'Scanning...' : 'Scan Files'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {hasScanned && (
          <div className="mb-8" ref={settingsRef}>
            <Card className="border-accent/30 border bg-white/85 shadow-lg backdrop-blur-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-3 text-xl text-gray-900">
                  <div className="gradient-accent rounded-lg p-2">
                    <SettingsIcon className="text-accent-foreground h-5 w-5" />
                  </div>
                  File Organization Settings
                </CardTitle>
                <CardDescription className="text-gray-700">
                  Customize how your {detectedFileTypes.reduce((sum, ft) => sum + ft.count, 0)}{' '}
                  detected files will be organized
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="extensions" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="extensions">
                      File Extensions ({detectedFileTypes.length})
                    </TabsTrigger>
                    <TabsTrigger value="folders">Folder Mapping</TabsTrigger>
                    <TabsTrigger value="unmapped">
                      Unmapped ({unmappedExtensions.length})
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="extensions" className="space-y-4">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {detectedFileTypes
                        .filter((ft) => !ft.isUnmapped)
                        .map((fileType) => (
                          <div
                            key={fileType.extension}
                            className={`rounded-xl border p-4 shadow-sm backdrop-blur-sm transition-all ${
                              fileType.enabled
                                ? 'border-green-200 bg-white/80'
                                : 'border-gray-200 bg-gray-50/80'
                            }`}
                          >
                            <div className="mb-3 flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={fileType.color}>{fileType.icon}</div>
                                <span className="font-mono font-bold text-gray-900">
                                  .{fileType.extension}
                                </span>
                              </div>
                              <Switch
                                checked={fileType.enabled}
                                onCheckedChange={() => toggleExtension(fileType.extension)}
                              />
                            </div>
                            <div className="mb-2 text-sm text-gray-600">
                              {fileType.count} files found
                            </div>
                            <div className="mb-3 text-xs text-gray-500">
                              → {fileType.customFolder || fileType.defaultFolder}/
                            </div>
                            <Input
                              placeholder="Custom folder name"
                              className="h-8 text-xs"
                              defaultValue={fileType.customFolder || fileType.defaultFolder}
                              onChange={(e) =>
                                updateCustomFolder(fileType.extension, e.target.value)
                              }
                            />
                          </div>
                        ))}
                    </div>
                  </TabsContent>

                  <TabsContent value="folders" className="space-y-4">
                    <div className="space-y-3">
                      {Array.from(
                        new Set(enabledExtensions.map((ft) => ft.customFolder || ft.defaultFolder))
                      ).map((folderName) => {
                        const extensionsInFolder = enabledExtensions.filter(
                          (ft) => (ft.customFolder || ft.defaultFolder) === folderName
                        )
                        const totalFilesInFolder = extensionsInFolder.reduce(
                          (sum, ft) => sum + ft.count,
                          0
                        )

                        return (
                          <div
                            key={folderName}
                            className="flex items-center justify-between rounded-xl border bg-white/60 p-4 shadow-sm backdrop-blur-sm"
                          >
                            <div className="flex items-center gap-4">
                              <FolderOpenIcon className="h-5 w-5 text-blue-500" />
                              <div>
                                <div className="font-medium text-gray-900">{folderName}/</div>
                                <div className="text-sm text-gray-600">
                                  {extensionsInFolder.map((ft) => `.${ft.extension}`).join(', ')}
                                  <span className="ml-2 text-gray-500">
                                    ({totalFilesInFolder} files)
                                  </span>
                                </div>
                              </div>
                            </div>
                            <Badge variant="outline" className="px-3 py-1">
                              {extensionsInFolder.length} extensions
                            </Badge>
                          </div>
                        )
                      })}
                    </div>
                  </TabsContent>

                  <TabsContent value="unmapped" className="space-y-4">
                    <div className="mb-4 rounded-lg border border-orange-200 bg-orange-50 p-4">
                      <div className="mb-2 flex items-center gap-2">
                        <AlertTriangleIcon className="h-5 w-5 text-orange-500" />
                        <span className="font-medium text-orange-800">
                          Unmapped Extensions Found
                        </span>
                      </div>
                      <p className="text-sm text-orange-700">
                        These file extensions don&apos;t have default folder mappings. Please assign
                        them to folders or exclude them from organization.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      {unmappedExtensions.map((fileType) => (
                        <div
                          key={fileType.extension}
                          className="rounded-xl border border-orange-200 bg-orange-50/50 p-4 shadow-sm backdrop-blur-sm"
                        >
                          <div className="mb-3 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="text-orange-500">{fileType.icon}</div>
                              <span className="font-mono font-bold text-gray-900">
                                .{fileType.extension}
                              </span>
                            </div>
                            <Switch
                              checked={fileType.enabled}
                              onCheckedChange={() => toggleExtension(fileType.extension)}
                            />
                          </div>
                          <div className="mb-3 text-sm text-gray-600">
                            {fileType.count} files found
                          </div>
                          <Input
                            placeholder="Assign to folder (e.g., Design, Graphics)"
                            className="mb-2 h-8 text-xs"
                            onChange={(e) => updateCustomFolder(fileType.extension, e.target.value)}
                          />
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 flex-1 bg-transparent text-xs"
                            >
                              <PlusIcon className="mr-1 h-3 w-3" />
                              Create New Folder
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </TabsContent>
                </Tabs>

                <div className="mt-6 flex items-center justify-center border-t border-gray-200 pt-6">
                  <div className="flex items-center gap-4">
                    <Button
                      onClick={handleStartOrganization}
                      disabled={
                        isRunning || !sourceFolder || !destinationFolder || totalEnabledFiles === 0
                      }
                      size="lg"
                      className="gradient-primary transform px-8 py-6 text-xl font-bold text-black shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:brightness-110"
                    >
                      <PlayIcon className="mr-2 h-5 w-5" />
                      Start Organization ({totalEnabledFiles} files)
                    </Button>
                    {isRunning && (
                      <Button
                        variant="outline"
                        onClick={() => setIsRunning(false)}
                        size="lg"
                        className="border-2 bg-transparent px-6 py-6"
                      >
                        <PauseIcon className="mr-2 h-5 w-5" />
                        Pause
                      </Button>
                    )}
                  </div>
                </div>

                {(isRunning || progress > 0) && (
                  <div className="gradient-secondary mt-6 rounded-xl p-6">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-secondary-foreground font-medium">
                        Organization Progress
                      </span>
                      <span className="text-secondary-foreground text-lg font-bold">
                        {Math.round(progress)}%
                      </span>
                    </div>
                    <Progress value={progress} className="mb-2 h-3" />
                    <div className="text-secondary-foreground/80 text-center text-sm">
                      {processedFiles} of {totalFiles} files processed
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        <div className="flex justify-center">
          <Card className="border-muted/30 w-full max-w-md border bg-white/85 shadow-lg backdrop-blur-md">
            <CardHeader className="pb-4">
              <CardTitle className="text-center text-lg text-gray-900">Current Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-center gap-3">
                {isScanning ? (
                  <>
                    <div className="h-3 w-3 animate-pulse rounded-full bg-blue-500" />
                    <span className="font-medium text-gray-800">Scanning files...</span>
                  </>
                ) : isRunning ? (
                  <>
                    <div className="h-3 w-3 animate-pulse rounded-full bg-green-500" />
                    <span className="font-medium text-gray-800">Processing files...</span>
                  </>
                ) : progress === 100 ? (
                  <>
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    <span className="font-medium text-gray-800">Organization complete</span>
                  </>
                ) : hasScanned ? (
                  <>
                    <div className="h-3 w-3 rounded-full bg-yellow-500" />
                    <span className="font-medium text-gray-800">Ready to organize</span>
                  </>
                ) : (
                  <>
                    <div className="bg-muted-foreground h-3 w-3 rounded-full" />
                    <span className="font-medium text-gray-800">Ready to scan</span>
                  </>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2">
                <div className="rounded-lg bg-white/40 p-3 text-center shadow-sm backdrop-blur-sm">
                  <div className="text-2xl font-bold text-gray-900">{processedFiles}</div>
                  <div className="text-sm text-gray-600">Processed</div>
                </div>
                <div className="rounded-lg bg-white/40 p-3 text-center shadow-sm backdrop-blur-sm">
                  <div className="text-2xl font-bold text-gray-900">
                    {hasScanned ? totalEnabledFiles : totalFiles}
                  </div>
                  <div className="text-sm text-gray-600">
                    {hasScanned ? 'Selected Files' : 'Found Files'}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
