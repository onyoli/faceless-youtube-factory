"use client";

import { ProjectDetail } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, Clock, User } from "lucide-react";

interface ScriptTabProps {
    project: ProjectDetail;
}

export function ScriptTab({ project }: ScriptTabProps) {
    const script = project.script;

    if (!script) {
        return (
            <Card>
                <CardContent className="py-12 text-center">
                    <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">Script is being generated...</p>
                </CardContent>
            </Card>
        );
    }

    const totalDuration = script.scenes.reduce((sum, scene) => sum + Number(scene.duration), 0);
    const speakers = [...new Set(script.scenes.map((s) => s.speaker))];

    return (
        <div className="space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
                <Card>
                    <CardContent className="py-4">
                        <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-primary" />
                            <span className="text-sm text-muted-foreground">Scenes</span>
                        </div>
                        <p className="text-2xl font-bold mt-1">{script.scenes.length}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="py-4">
                        <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-primary" />
                            <span className="text-sm text-muted-foreground">Duration</span>
                        </div>
                        <p className="text-2xl font-bold mt-1">
                            {Math.floor(totalDuration / 60)}:{String(Math.floor(totalDuration % 60)).padStart(2, "0")}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="py-4">
                        <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-primary" />
                            <span className="text-sm text-muted-foreground">Speakers</span>
                        </div>
                        <p className="text-2xl font-bold mt-1">{speakers.length}</p>
                    </CardContent>
                </Card>
            </div>

            {/* Script Content */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                        <span>Script v{script.version}</span>
                        <div className="flex gap-2">
                            {speakers.map((speaker) => (
                                <Badge key={speaker} variant="secondary">{speaker}</Badge>
                            ))}
                        </div>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {script.scenes.map((scene, index) => (
                            <div key={index} className="p-4 rounded-lg bg-secondary/30 border">
                                <div className="flex items-center justify-between mb-2">
                                    <Badge variant="outline">{scene.speaker}</Badge>
                                    <span className="text-xs text-muted-foreground">{scene.duration}s</span>
                                </div>
                                <p className="text-sm">{scene.line}</p>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}