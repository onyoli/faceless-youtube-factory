import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
    return (
        <div className="flex items-center justify-center min-h-[70vh]">
            <SignUp
                appearance={{
                    elements: {
                        formButtonPrimary: "bg-primary hover:bg-primary/90",
                        card: "bg-card border border-border",
                        headerTitle: "text-foreground",
                        headerSubtitle: "text-muted-foreground",
                        socialButtonsBlockButton: "border-border hover:bg-secondary",
                        formFieldLabel: "text-foreground",
                        formFieldInput: "bg-background border-border text-foreground",
                        footerActionLink: "text-primary hover:text-primary/90",
                    },
                }}
            />
        </div>
    );
}
