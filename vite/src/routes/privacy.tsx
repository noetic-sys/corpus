import { createFileRoute, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/privacy')({
  component: PrivacyPolicyPage,
})

function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-6 py-16">
        {/* Header */}
        <div className="mb-12">
          <Link to="/landing" className="text-sm text-muted-foreground hover:text-foreground mb-4 inline-block">
            &larr; Back to Home
          </Link>
          <h1 className="text-4xl font-bold tracking-tight text-foreground mb-2">
            Privacy Policy
          </h1>
          <p className="text-muted-foreground">
            Effective Date: January 1, 2025<br />
            Last Modified: January 1, 2025
          </p>
        </div>

        {/* Content */}
        <div className="prose prose-neutral dark:prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
            <p className="text-muted-foreground leading-relaxed">
              Corpus (the "Service") is a web application developed by Noetic Systems, LLC ("We/Us") that
              allows you ("Users") to upload documents and analyze them with Artificial Intelligence ("AI").
              The Service interfaces with any number of Artificial Intelligence providers to analyze documents,
              including, but not limited to Anthropic, OpenAI, Google, and xAI, and Stripe ("Payment Processor")
              to process subscriptions and other payments.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              We take Users' privacy seriously. We know that Users care how their information is used and shared.
              This privacy policy (the "Policy") describes how We collect, use, and share Users' personal
              information through the Service's web application at onecorpus.com and related features. By using
              or accessing the Service in any manner, Users accept these practices and policies, and Users agree
              to the Service's collection, use, and sharing of their information as described in the Policy.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              We may update the Policy at any time, without prior notice. The date of last modification will be
              posted at the beginning of the Policy, and We may provide notice via the Service that the Policy
              has changed. By continuing to use the Service, Users agree to any modifications to the Policy.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Unless otherwise indicated, all terms have the same definitions as those in the Service's{' '}
              <Link to="/terms" className="text-foreground hover:underline">Terms of Service</Link>,
              the agreement that governs Users' access to the Services.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Information We Process</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              We believe in processing only the minimum information needed to operate the Service and for
              Users to enjoy a positive user experience. We do not routinely access information that Users
              generate via the Service. When Users use the Service, only the following information is sent to us:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>
                <em>Information Processed On Sign Up</em> – Once the User signs up for the Service, we collect
                basic profile information from Google, if signing up through OAuth, including their name, email,
                and avatar profile URL. We do not sell this information.
              </li>
              <li>
                <em>Information Processed On Purchase</em> – Once users purchase a subscription plan through Stripe,
                we collect a reference to this subscription to accurately update their experience in the Service.
                Any billing details are stored securely with the Payment Processor.
              </li>
              <li>
                <em>Documents and Content</em> – Users may upload documents (PDFs, web pages) to the Service for
                analysis. These documents are stored securely and processed only to provide the Service.
              </li>
              <li>
                <em>Questions and Queries</em> – Questions Users submit and AI-generated responses are stored
                to provide the Service and maintain Users' workspaces.
              </li>
              <li>
                <em>Communications with the Service</em> – If Users contact Us, the Service may retain a record
                of that communication and its content.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. AI-Generated Content</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service allows Users to analyze documents and receive AI-generated responses with assistance
              from Artificial Intelligence providers. As such, by using the Service, Users agree to adhere to
              relevant Terms and Conditions imposed by the model providers, namely Anthropic, OpenAI, Google,
              and xAI, specifically around prohibited content and violations of these policies. Users agree to
              adhere to these Terms, and release Noetic Systems, LLC from any liability related to these terms
              on their behalf. The Service is not responsible for anything Users choose to generate in the
              Service that may be inaccurate, misleading, or in violation of other terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Information Shared with or Available to Third Parties</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              To provide document analysis and question answering capabilities, Users' documents and queries
              may be processed by third-party AI providers. These providers include:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li><strong>Anthropic</strong> – For language model processing</li>
              <li><strong>OpenAI</strong> – For language model processing and embeddings</li>
              <li><strong>Google</strong> – For language model processing (Gemini)</li>
              <li><strong>xAI</strong> – For language model processing (Grok)</li>
              <li><strong>Voyage AI</strong> – For document embeddings</li>
              <li><strong>Exa</strong> – For web search queries</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              Users' names and payment information is collected by the Payment Processor upon purchasing,
              updating, or cancelling any subscription plan. By using the Service, Users release the Service
              from any liability should the Payment Processor or AI providers misuse or expose their information
              in any way.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Purchase Finality</h2>
            <p className="text-muted-foreground leading-relaxed">
              All purchases made through the Service are final. Users may contact the Service should they feel
              that there is a mistake, but by using the Service, Users agree that the Service is not liable for
              any accidental or fraudulent purchases. Users also agree to not act fraudulently with purchases
              made on the Service, such as chargeback fraud. Users identified having violated these terms will
              have their accounts deactivated. Users who cancel a subscription will have the availability to
              use the Service until the end of their current subscription period.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. How We Use Information</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              We may use the information collected in order to operate, develop, research, modify, and improve
              the Service and any other related services. This may include using Users' information to:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Provide Services that Users request</li>
              <li>Maintain a record of any information Users share with the Service and communications Users send to the Service</li>
              <li>Provide administrative notices applicable to Users' use of the Service</li>
              <li>Respond to Users' questions and comments and provide support</li>
              <li>Analyze trends in statistics regarding usage of the Service</li>
              <li>Protect against and prevent infringement, unauthorized use and access of the Service, and claims and other liabilities</li>
              <li>Analyze crash reports and diagnostic logs to improve the Service</li>
              <li>Enforce the Service's Terms of Service and this Policy</li>
              <li>Comply with applicable legal requirements, court orders, legal proceedings, and document requests</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Data Retention</h2>
            <p className="text-muted-foreground leading-relaxed">
              We retain Users' data for as long as their account is active or as needed to provide services.
              Users may delete their documents and data at any time through the application. Upon account
              deletion, we will remove Users' personal data within 30 days, except where retention is
              required by law.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Children Under 18 Years of Age</h2>
            <p className="text-muted-foreground leading-relaxed">
              Children under the age of 18 are not permitted to use, access, or register for the Service in
              any way. The Service does not knowingly collect or solicit information from anyone under the
              age of 18. If we become aware that a person under 18 has provided or attempted to provide us
              with personal information, we will use best efforts to remove the information permanently from
              our files without prior notice.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Changes to This Policy</h2>
            <p className="text-muted-foreground leading-relaxed">
              If We decide to change this Policy, We will post those changes on this page. If we make material
              changes to how the Service treats Users' personal information, we will notify Users through a
              notice on the Services. The effective date of the current version will be posted at the top of
              this Policy. Please check this website periodically for updates as such modifications may affect
              Users' ability to use, access, or interact with the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Contact Us</h2>
            <p className="text-muted-foreground leading-relaxed">
              If Users have any questions about this Policy, please contact Us at{' '}
              <a href="mailto:privacy@onecorpus.com" className="text-foreground hover:underline">privacy@onecorpus.com</a>.
            </p>
            <p className="text-muted-foreground leading-relaxed mt-4">
              Noetic Systems, LLC<br />
              United States
            </p>
          </section>
        </div>

        {/* Footer Navigation */}
        <div className="mt-16 pt-8 border-t">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <Link to="/terms" className="hover:text-foreground">Terms of Service</Link>
            <span>&copy; {new Date().getFullYear()} Noetic Systems, LLC</span>
          </div>
        </div>
      </div>
    </div>
  )
}
