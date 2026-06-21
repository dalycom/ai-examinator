import { LoginForm } from "@/components/auth/login-form";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function LoginPage({ params }: Props) {
  await params;
  return <LoginForm />;
}
