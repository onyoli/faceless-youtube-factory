"use client";

import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";
import { ProjectDetail } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter
} from "@/components/ui/dialog";
import { Loader2, Save, RefreshCw, Folder } from "lucide-react";

interface EditProjectModalProps {
    project: ProjectDetail;
    open: boolean;
    onClose: () => void;
}

export function EditProjectModal({ project, open, onClose }: EditProjectModalProps) {
    const api = useApi();
    const queryClient = useQueryClient();

    const [title, setTitle] = useState(project.title);
    const [category, setCategory] = useState(project.category || "");
    const [scriptPrompt, setScriptPrompt] = useState(
        project.settings?.script_prompt || ""
    );

    // Reset form when project changes
    useEffect(() => {
        setTitle(project.title);
        setCategory(project.category || "");
        setScriptPrompt(project.settings?.script_prompt || "");
    }, [project]);

    const updateMutation = useMutation({
        mutationFn: ({ regenerate }: { regenerate: boolean }) =>
            api.updateProject(
                project.id,
                {
                    title: title !== project.title ? title : undefined,
                    category: category !== (project.category || "") ? category : undefined,
                    script_prompt: scriptPrompt !== (project.settings?.script_prompt || "") ? scriptPrompt : undefined,
                },
                regenerate
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["project", project.id] });
            onClose();
        },
    });

    const handleSave = () => {
        updateMutation.mutate({ regenerate: false });
    };

    const handleSaveAndRegenerate = () => {
        updateMutation.mutate({ regenerate: true });
    };

    const hasChanges =
        title !== project.title ||
        category !== (project.category || "") ||
        scriptPrompt !== (project.settings?.script_prompt || "");

    const isPending = updateMutation.isPending;

    return (
        <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Edit Project</DialogTitle>
                    <DialogDescription>
                        Update project details. Use "Save & Regenerate" to create a new video with updated settings.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    {/* Title */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Title</label>
                        <Input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Video title"
                            maxLength={255}
                        />
                    </div>

                    {/* Category */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium flex items-center gap-2">
                            <Folder className="h-4 w-4" />
                            Category
                        </label>
                        <Input
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            placeholder="e.g., Tech Videos, Gaming, Tutorials"
                            maxLength={100}
                        />
                    </div>

                    {/* Script Prompt */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Video Prompt</label>
                        <Textarea
                            value={scriptPrompt}
                            onChange={(e) => setScriptPrompt(e.target.value)}
                            placeholder="Describe what your video should be about..."
                            className="min-h-[150px]"
                            maxLength={5000}
                        />
                        <p className="text-xs text-muted-foreground">
                            {scriptPrompt.length}/5000 characters
                        </p>
                    </div>
                </div>

                {updateMutation.isError && (
                    <p className="text-sm text-destructive">
                        {(updateMutation.error as Error).message}
                    </p>
                )}

                <DialogFooter className="gap-2 sm:gap-0">
                    <Button
                        variant="outline"
                        onClick={onClose}
                        disabled={isPending}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="secondary"
                        onClick={handleSave}
                        disabled={isPending || !hasChanges}
                    >
                        {isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                            <Save className="h-4 w-4 mr-2" />
                        )}
                        Save
                    </Button>
                    <Button
                        onClick={handleSaveAndRegenerate}
                        disabled={isPending || !scriptPrompt.trim()}
                    >
                        {isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                            <RefreshCw className="h-4 w-4 mr-2" />
                        )}
                        Save & Regenerate
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
