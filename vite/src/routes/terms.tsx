import { createFileRoute, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/terms')({
  component: TermsOfServicePage,
})

function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-6 py-16">
        {/* Header */}
        <div className="mb-12">
          <Link to="/landing" className="text-sm text-muted-foreground hover:text-foreground mb-4 inline-block">
            &larr; Back to Home
          </Link>
          <h1 className="text-4xl font-bold tracking-tight text-foreground mb-2">
            Terms of Service
          </h1>
          <p className="text-muted-foreground">
            Effective Date: January 1, 2026<br />
            Last Modified: January 1, 2026
          </p>
        </div>

        {/* Content */}
        <div className="prose prose-neutral dark:prose-invert max-w-none space-y-8">
          <section>
            <p className="text-muted-foreground leading-relaxed">
              Welcome to Corpus (the "Service"). The following Terms of Service (the "Terms") between
              you ("Users") and Noetic Systems, LLC ("We/Us") govern Users' use of and access to the
              Service's web application at onecorpus.com and related features (collectively, the "Services").
            </p>
            <p className="text-muted-foreground leading-relaxed">
              These Terms constitute a binding agreement made between Us and Users. These Terms will
              remain in effect while Users use the Services. <em>By using or accessing any part of the Services,
              Users agree to the Terms herein or incorporated by reference. If Users do not agree to all of
              these Terms, they should not use or access the Services.</em>
            </p>
            <p className="text-muted-foreground leading-relaxed font-medium">
              PLEASE NOTE THAT, EXCEPT AS PROVIDED BELOW, THESE TERMS REQUIRE RESOLUTION OF
              DISPUTES THROUGH USE OF AN ARBITRATION SERVICE. USERS HEREBY AGREE THAT ALL
              DISPUTES ARISING FROM, RELATED TO, OR IN CONNECTION WITH THEIR USE OF THE SERVICES
              WILL BE RESOLVED IN ACCORDANCE WITH THE ARBITRATION AND GOVERNING LAW
              PROVISIONS SET FORTH IN SECTION 14 BELOW.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Modification</h2>
            <p className="text-muted-foreground leading-relaxed">
              We reserve the right, at Our sole discretion, to modify these Terms at any time and without
              prior notice. If We modify these Terms, We will either post a notification of the modification on
              this website or otherwise provide Users with notice of the change. The date of the last
              modification will also be posted at the beginning of these Terms. It is Users' responsibility to
              check from time to time for updates. By continuing to access or use the Services, Users agree to
              be bound by any modified Terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Privacy Policy</h2>
            <p className="text-muted-foreground leading-relaxed">
              Users' use of the Services signifies their continuing consent to the Corpus{' '}
              <Link to="/privacy" className="text-foreground hover:underline">privacy policy</Link>,
              which discusses how We collect, use, and share information through the Services. Users should
              read the privacy policy carefully.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. Eligibility</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Services are intended solely for persons who are at least 18 years old. By using the Services,
              Users represent and warrant that they are at least the age of 18. If we become aware that a
              person under 18 has provided or attempted to provide us with personal information, we will use
              best efforts to remove the information permanently from our files without prior notice.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Acceptable Uses</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Users' use of the Services is subject to their compliance with these Terms. As part of the
              features of the Services, we allow Users to upload documents and use Artificial Intelligence
              to analyze them ("User Content"). Users' use of the Services, including Users'
              transmission of User Content, is further subject to the following terms:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Users may not use the Services to harm other people or their property, or to transmit
                User Content that in any way infringes or violates the rights of anyone, including
                without limitation any intellectual property rights, rights of privacy or publicity, or
                rights in confidential information of any person.</li>
              <li>Users may not use the Services to insult, harass, annoy, abuse, or attack users or other persons.</li>
              <li>Users may not use the Services in any way that violates the OpenAI Terms of Service.</li>
              <li>Users may not use the Services in any way that violates the Anthropic Terms of Service.</li>
              <li>Users may not use the Services in any way that violates the Google Terms of Service.</li>
              <li>Users may not use the Services to generate harmful, illegal, or inappropriate content.</li>
              <li>Users may not upload documents containing malware, viruses, or harmful code.</li>
              <li>Users may not upload documents they do not have the legal right to use.</li>
              <li>Users may not interfere with or damage the Services or any other Users' enjoyment of
                the Services, including, without limitation, through the use of viruses, bots, harmful
                code, denial-of-service attacks, backdoors, packet or IP address spoofing, forged
                routing, or any similar methods or technology.</li>
              <li>Users may not use the Services for the purpose of exploiting, harming, or attempting
                to exploit or harm minors in any way.</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              We reserve the right to modify, delete, or otherwise alter User Content if it violates the
              acceptable uses as detailed in this Section.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Your Content</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              You retain ownership of all documents and content you upload to the Service ("Your Content").
              By uploading content, you grant us a limited license to process, store, and analyze Your Content
              solely for the purpose of providing the Service to you.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              You represent and warrant that you have all necessary rights to upload Your Content and that
              Your Content does not violate any third party's rights.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. AI-Generated Content</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The Service allows Users to analyze documents and receive AI-generated responses with assistance from
              Artificial Intelligence providers. As such, by using the Service, Users agree to adhere to relevant Terms and
              Conditions imposed by the model providers, namely OpenAI, Anthropic, Google, and xAI, specifically around
              prohibited content and violations of these policies. Users agree to adhere to these Terms, and release
              Noetic Systems, LLC from any liability related to these terms on their behalf.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The Service is not responsible for anything Users choose to generate in the Service that may be
              inaccurate, misleading, or in violation of other terms. USERS ACKNOWLEDGE THAT WE HAVE NO CONTROL
              OVER AND DO NOT GUARANTEE THE QUALITY, SAFETY, ACCURACY OR LEGALITY OF ANY AI-GENERATED CONTENT.
              WE HAVE NO RESPONSIBILITY TO USERS FOR, AND HEREBY DISCLAIM ALL LIABILITY ARISING FROM, THE
              CONTENTS OF ANY AI-GENERATED RESPONSES.
            </p>
            <p className="text-muted-foreground leading-relaxed font-medium">
              USERS UNDERSTAND AND AGREE THAT AI-GENERATED CONTENT MAY CONTAIN ERRORS, INACCURACIES,
              HALLUCINATIONS, OR FABRICATED INFORMATION. BY USING THE SERVICE, USERS CHOOSE TO ASSUME
              THESE RISKS VOLUNTARILY. AI RESPONSES ARE NOT PROFESSIONAL ADVICE OF ANY KIND.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Third-Party Services</h2>
            <p className="text-muted-foreground leading-relaxed">
              As part of the Services, We may integrate with third party AI providers and services. Users agree that
              We are not responsible or liable for any content or other materials from third parties. We are
              also not responsible for any transactions or dealings between Users and any third party. Users
              agree that We are not responsible for any claim or loss due to a third-party service or provider.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Intellectual Property and Open Source</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The Corpus source code is available under the GNU Affero General Public License v3.0 (AGPL-3.0).
              Your rights to use, modify, and distribute the source code are governed by that license,
              not these Terms. These Terms govern your use of the hosted Service at onecorpus.com.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              The Corpus name, logo, and branding are trademarks of Noetic Systems, LLC and are not
              covered by the AGPL license. You may not use our trademarks without explicit written permission.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Fees, Subscriptions, and Purchase Finality</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Users are responsible for any fees incurred when they make a purchase with the Services.
              Certain features of the Service may require a paid subscription.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              All purchases made through the Service are final. Users may contact Us should they feel that there is a
              mistake, but by using the Service, Users agree that the Service is not liable for any accidental or fraudulent
              purchases. Users also agree to not act fraudulently with purchases made on the Service, such as chargeback
              fraud. Users identified having violated these terms will have their accounts deactivated. Users who
              cancel a subscription will have the availability to use the Service until the end of their current subscription
              period.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Warranties</h2>
            <p className="text-muted-foreground leading-relaxed mb-4 font-medium">
              WE PROVIDE THE SERVICES "AS IS." WE MAKE NO EXPRESS WARRANTIES OR GUARANTEES
              ABOUT THE SERVICES. TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE DISCLAIM EXPRESS
              AND IMPLIED WARRANTIES, INCLUDING ANY IMPLIED WARRANTIES OF MERCHANTABILITY,
              SATISFACTORY QUALITY, ACCURACY, TIMELINESS, FITNESS FOR A PARTICULAR PURPOSE, OR
              NON-INFRINGEMENT. WE DO NOT GUARANTEE THAT THIS SERVICE WILL MEET
              USERS' REQUIREMENTS, IS ERROR-FREE, RELIABLE, OR WILL OPERATE WITHOUT INTERRUPTION.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4 font-medium">
              USERS ASSUME ALL RISKS WITH THEIR USE OF THE SERVICES, INCLUDING BUT NOT LIMITED TO
              RISKS RELATING TO ANY INACCURATE, MISLEADING, OR FABRICATED AI-GENERATED CONTENT.
              WE MAKE NO WARRANTIES WITH RESPECT TO THE ACCURACY OR COMPLETENESS OF ANY
              AI-GENERATED RESPONSES OR CITATIONS.
            </p>
            <p className="text-muted-foreground leading-relaxed font-medium">
              BECAUSE SOME STATES DO NOT PERMIT DISCLAIMER OF IMPLIED WARRANTIES, USERS MAY
              HAVE ADDITIONAL CONSUMER RIGHTS UNDER LOCAL LAWS.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Limitation on Liability</h2>
            <p className="text-muted-foreground leading-relaxed mb-4 font-medium">
              TO THE MAXIMUM EXTENT ALLOWED BY LAW, WE SHALL NOT BE LIABLE TO USERS OR TO ANY
              THIRD PARTIES FOR ANY INDIRECT, SPECIAL, INCIDENTAL, CONSEQUENTIAL, PUNITIVE, OR
              EXEMPLARY DAMAGES, EVEN IF WE KNEW OR SHOULD HAVE KNOWN OF THE POSSIBILITY OF
              SUCH DAMAGES. THIS LIMITATION APPLIES WHETHER BASED ON A CLAIM RELATED TO A
              WARRANTY, CONTRACT, TORT, PRODUCT LIABILITY, OR ANY OTHER LEGAL THEORY, AND
              WHETHER OR NOT WE KNEW, SHOULD HAVE KNOWN, OR WERE APPRISED OF SUCH DAMAGES.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4 font-medium">
              IN NO CIRCUMSTANCE WILL OUR AGGREGATE LIABILITY ARISING OUT OF OR IN CONNECTION
              WITH THESE TERMS OR THE USE OF THE SERVICES EXCEED FIFTY U.S. DOLLARS ($50).
            </p>
            <p className="text-muted-foreground leading-relaxed font-medium">
              BECAUSE SOME STATES DO NOT ALLOW THE EXCLUSION OR THE LIMITATION OF LIABILITY FOR
              CERTAIN DAMAGES, IN SUCH STATES, OUR LIABILITY SHALL BE LIMITED TO THE FULL EXTENT
              PERMITTED BY LAW.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Severability and Integration</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Terms constitute the entire agreement between Us and Users with respect to use of the
              Services, and supersede all previous written or oral agreements (including prior versions of the
              Terms). If any part of the Terms is held invalid or unenforceable, that portion shall be construed
              in a manner consistent with applicable law to reflect, as nearly as possible, the original
              intentions of the parties, and the remaining portions shall remain in full force and effect.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">13. No Waiver and Assignment</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Our failure to exercise or enforce any right or provision of these Terms shall not constitute a
              waiver of such right or provision, and no waiver of any of the provisions of these Terms shall be
              deemed a further or continuing waiver of such provision or any other provision.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Users may not assign or transfer these Terms, by operation of law or otherwise, without Our
              prior written consent. Any attempt by Users to assign or transfer these Terms without such
              consent will be null and of no effect. We may assign or transfer these Terms, at Our sole
              discretion, without restriction. Subject to the foregoing, these Terms will bind and inure to the
              benefit of the parties, their successors and permitted assigns. These Terms do not and are not
              intended to confer any rights or remedies upon any person other than the parties.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">14. Arbitration</h2>
            <p className="text-muted-foreground leading-relaxed">
              Any controversy or claim arising out of or relating to this contract, or the breach thereof, shall
              be settled by arbitration administered by the American Arbitration Association in accordance
              with its Commercial Arbitration Rules, and judgment on the award rendered by the arbitrator(s)
              may be entered in any court having jurisdiction thereof.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">15. Governing Law</h2>
            <p className="text-muted-foreground leading-relaxed">
              These Terms (and any further guidelines, rules, or policies incorporated therein) shall be
              governed and construed according to the laws of the State of Delaware and the
              federal laws of the United States.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">16. Contact Us</h2>
            <p className="text-muted-foreground leading-relaxed">
              If Users have any questions about these Terms, please contact Us at{' '}
              <a href="mailto:legal@onecorpus.com" className="text-foreground hover:underline">legal@onecorpus.com</a>.
            </p>
            <p className="text-muted-foreground leading-relaxed mt-4">
              Domain name: onecorpus.com
            </p>
          </section>
        </div>

        {/* Footer Navigation */}
        <div className="mt-16 pt-8 border-t">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <Link to="/privacy" className="hover:text-foreground">Privacy Policy</Link>
            <span>&copy; {new Date().getFullYear()} Noetic Systems, LLC</span>
          </div>
        </div>
      </div>
    </div>
  )
}
