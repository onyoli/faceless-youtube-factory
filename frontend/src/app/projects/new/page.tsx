"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createProject, getYouTubeConnection } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Sparkles, Youtube, Image } from "lucide-react";

export default function NewProjectPage() {
    const router = useRouter();
    const [title, setTitle] = useState("");
    const [prompt, setPrompt] = useState("");
    const [autoUpload, setAutoUpload] = useState(false);
    const [scenesPerImage, setScenesPerImage] = useState(2);

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

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate({
            title,
            script_prompt: prompt,
            auto_upload: autoUpload,
            scenes_per_image: scenesPerImage,
        });
    };

    const examplePrompts = [
        "Create a 3-minute video explaining quantum computing for beginners with a Host and an Expert",
        "Make a funny educational video about why cats love boxes, with two comedic hosts bantering",
        "Generate a motivational video about building daily habits, with an inspiring narrator",
    ];

    const ratioOptions = [
        { value: 1, label: "1:1 (One image per scene)", description: "Highest quality, more images" },
        { value: 2, label: "1:2 (One image per 2 scenes)", description: "Balanced (recommended)" },
        { value: 3, label: "1:3 (One image per 3 scenes)", description: "Faster generation" },
        { value: 5, label: "1:5 (One image per 5 scenes)", description: "Fastest, fewer images" },
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
                        {/* Image Ratio Selector */}
                        <div className="space-y-3">
                            <label className="text-sm font-medium flex items-center gap-2">
                                <Image className="h-4 w-4" />
                                Image Generation Ratio
                            </label>
                            <div className="grid grid-cols-2 gap-2">
                                {ratioOptions.map((option) => (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setScenesPerImage(option.value)}
                                        className={`text-left p-3 rounded-lg border transition-colors ${scenesPerImage === option.value
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
                            disabled={createMutation.isPending || !title || !prompt}
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