"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createProject, getYouTubeConnection, uploadBackgroundImage } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Sparkles, Youtube, Image, Upload, X } from "lucide-react";

type ImageMode = "per_scene" | "single" | "upload" | "none";

export default function NewProjectPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [title, setTitle] = useState("");
    const [prompt, setPrompt] = useState("");
    const [autoUpload, setAutoUpload] = useState(false);
    const [imageMode, setImageMode] = useState<ImageMode>("per_scene");
    const [scenesPerImage, setScenesPerImage] = useState(2);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState(false);

    const { data: ytConnection } = useQuery({
        queryKey: ["youtube-connection"],
        queryFn: getYouTubeConnection,
    });

    const createMutation = useMutation({
        mutationFn: createProject,
        onSuccess: (project) => {
            router.push(`/projects/${project.id}`);
        },
    });

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        try {
            const result = await uploadBackgroundImage(file);
            setUploadedFile(file);
            setUploadedUrl(result.url);
        } catch (error) {
            console.error("Upload failed:", error);
        } finally {
            setIsUploading(false);
        }
    };

    const handleRemoveFile = () => {
        setUploadedFile(null);
        setUploadedUrl(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate({
            title,
            script_prompt: prompt,
            auto_upload: autoUpload,
            image_mode: imageMode,
            scenes_per_image: imageMode === "per_scene" ? scenesPerImage : undefined,
            background_image_url: imageMode === "upload" ? uploadedUrl || undefined : undefined,
        });
    };

    const examplePrompts = [
        "Create a 3-minute video explaining quantum computing for beginners with a Host and an Expert",
        "Make a funny educational video about why cats love boxes, with two comedic hosts bantering",
        "Generate a motivational video about building daily habits, with an inspiring narrator",
    ];

    const imageModeOptions = [
        { value: "per_scene" as ImageMode, label: "Per Scene", description: "Generate multiple images based on ratio" },
        { value: "single" as ImageMode, label: "Single Image", description: "One AI image for entire video" },
        { value: "upload" as ImageMode, label: "Upload", description: "Use your own background image" },
        { value: "none" as ImageMode, label: "No Images", description: "Solid color backgrounds (fastest)" },
    ];

    const ratioOptions = [
        { value: 1, label: "1:1", description: "One image per scene" },
        { value: 2, label: "1:2", description: "One image per 2 scenes" },
        { value: 3, label: "1:3", description: "One image per 3 scenes" },
        { value: 5, label: "1:5", description: "One image per 5 scenes" },
    ];

    return (
        <div className="max-w-2xl mx-auto">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-primary" />
                        Create New Video
                    </CardTitle>
                    <CardDescription>
                        Describe your video idea and AI will generate the script, voices, and final video
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* Title */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Video Title</label>
                            <Input
                                placeholder="My Awesome Video"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                required
                                maxLength={255}
                            />
                        </div>

                        {/* Prompt */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Video Description</label>
                            <Textarea
                                placeholder="Describe what your video should be about..."
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                required
                                minLength={10}
                                maxLength={5000}
                                className="min-h-[150px]"
                            />
                            <p className="text-xs text-muted-foreground">
                                {prompt.length}/5000 characters
                            </p>
                        </div>

                        {/* Example Prompts */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">
                                Example prompts (click to use)
                            </label>
                            <div className="space-y-2">
                                {examplePrompts.map((example, i) => (
                                    <button
                                        key={i}
                                        type="button"
                                        onClick={() => setPrompt(example)}
                                        className="w-full text-left text-sm p-3 rounded-lg border border-border hover:border-primary/50 hover:bg-secondary/50 transition-colors"
                                    >
                                        {example}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Image Mode Selector */}
                        <div className="space-y-3">
                            <label className="text-sm font-medium flex items-center gap-2">
                                <Image className="h-4 w-4" />
                                Background Images
                            </label>
                            <div className="grid grid-cols-2 gap-2">
                                {imageModeOptions.map((option) => (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setImageMode(option.value)}
                                        className={`text-left p-3 rounded-lg border transition-colors ${imageMode === option.value
                                            ? "border-primary bg-primary/10"
                                            : "border-border hover:border-primary/50"
                                            }`}
                                    >
                                        <span className="text-sm font-medium">{option.label}</span>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {option.description}
                                        </p>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Ratio Selector (only for per_scene mode) */}
                        {imageMode === "per_scene" && (
                            <div className="space-y-3">
                                <label className="text-sm font-medium">Image Ratio</label>
                                <div className="flex gap-2">
                                    {ratioOptions.map((option) => (
                                        <button
                                            key={option.value}
                                            type="button"
                                            onClick={() => setScenesPerImage(option.value)}
                                            className={`flex-1 p-2 rounded-lg border transition-colors text-center ${scenesPerImage === option.value
                                                ? "border-primary bg-primary/10"
                                                : "border-border hover:border-primary/50"
                                                }`}
                                        >
                                            <span className="text-sm font-medium">{option.label}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* File Upload (only for upload mode) */}
                        {imageMode === "upload" && (
                            <div className="space-y-3">
                                <label className="text-sm font-medium">Background Image</label>
                                {uploadedFile ? (
                                    <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
                                        <Image className="h-5 w-5 text-primary" />
                                        <span className="flex-1 text-sm truncate">{uploadedFile.name}</span>
                                        <button
                                            type="button"
                                            onClick={handleRemoveFile}
                                            className="p-1 rounded hover:bg-secondary"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                ) : (
                                    <button
                                        type="button"
                                        onClick={() => fileInputRef.current?.click()}
                                        disabled={isUploading}
                                        className="w-full p-6 rounded-lg border-2 border-dashed border-border hover:border-primary/50 transition-colors flex flex-col items-center gap-2"
                                    >
                                        {isUploading ? (
                                            <Loader2 className="h-6 w-6 animate-spin" />
                                        ) : (
                                            <Upload className="h-6 w-6 text-muted-foreground" />
                                        )}
                                        <span className="text-sm text-muted-foreground">
                                            {isUploading ? "Uploading..." : "Click to upload image"}
                                        </span>
                                    </button>
                                )}
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/jpeg,image/png,image/webp"
                                    onChange={handleFileSelect}
                                    className="hidden"
                                />
                            </div>
                        )}

                        {/* Auto-upload option */}
                        {ytConnection?.connected && (
                            <div className="flex items-center gap-3 p-4 rounded-lg bg-secondary/50">
                                <input
                                    type="checkbox"
                                    id="auto-upload"
                                    checked={autoUpload}
                                    onChange={(e) => setAutoUpload(e.target.checked)}
                                    className="h-4 w-4 rounded border-border"
                                />
                                <label htmlFor="auto-upload" className="flex items-center gap-2 text-sm">
                                    <Youtube className="h-4 w-4 text-red-500" />
                                    Auto-upload to YouTube when ready
                                </label>
                            </div>
                        )}

                        {/* Submit */}
                        <Button
                            type="submit"
                            className="w-full"
                            disabled={
                                createMutation.isPending ||
                                !title ||
                                !prompt ||
                                (imageMode === "upload" && !uploadedUrl)
                            }
                        >
                            {createMutation.isPending ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                <>
                                    <Sparkles className="h-4 w-4" />
                                    Generate Video
                                </>
                            )}
                        </Button>

                        {createMutation.isError && (
                            <p className="text-sm text-destructive text-center">
                                {(createMutation.error as Error).message}
                            </p>
                        )}
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}