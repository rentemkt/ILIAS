<?php

/**
 * This file is part of ILIAS, a powerful learning management system
 * published by ILIAS open source e-Learning e.V.
 *
 * ILIAS is licensed with the GPL-3.0,
 * see https://www.gnu.org/licenses/gpl-3.0.en.html
 * You should have received a copy of said license along with the
 * source code, too.
 *
 * If this is not the case or you just want to try ILIAS, you'll find
 * us at:
 * https://www.ilias.de
 * https://github.com/ILIAS-eLearning
 *
 *********************************************************************/

declare(strict_types=1);

namespace ILIAS\Administration;

use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class InstanceIdentityTest extends TestCase
{
    public static function names(): array
    {
        return [
            'unset' => [null, 'ILIAS'],
            'empty' => ['', 'ILIAS'],
            'whitespace only' => [" \t\r\n", 'ILIAS'],
            'configured' => ['Example Campus', 'Example Campus'],
            'trimmed' => [" \tExample Campus\n", 'Example Campus'],
            'internal whitespace' => ['Example  Campus', 'Example  Campus'],
            'unicode' => [' Campus São Paulo – 学校 ', 'Campus São Paulo – 学校'],
            'zero is a name' => ['0', '0'],
        ];
    }

    #[DataProvider('names')]
    public function testNameUsesConfiguredIdentityOrDefault(?string $configured, string $expected): void
    {
        $this->assertSame($expected, InstanceIdentity::name($configured));
    }

    public static function labels(): array
    {
        return [
            'fallback' => ['Log in to %s', null, 'Log in to ILIAS'],
            'trimmed name' => ['Log in to %s', ' Example Campus ', 'Log in to Example Campus'],
            'translated template' => ['Entrar em %s', 'Campus São Paulo', 'Entrar em Campus São Paulo'],
            'repeated placeholder' => ['%s logo - return to %s', 'Example Campus', 'Example Campus logo - return to Example Campus'],
            'literal percentage in name' => ['Log in to %s', '100% Example Campus', 'Log in to 100% Example Campus'],
            'literal percentage in template' => ['100% ready: %s', 'Example Campus', '100% ready: Example Campus'],
            'name is not a template' => ['Log in to %s', 'Example %s Campus', 'Log in to Example %s Campus'],
            'other percent tokens' => ['%d / %% / %1$s / %s', 'Example Campus', '%d / %% / %1$s / Example Campus'],
            'no placeholder' => ['Welcome', 'Example Campus', 'Welcome'],
            'empty template' => ['', 'Example Campus', ''],
            'plain text for UI renderer' => ['Log in to %s', 'Example <Campus> & "School"', 'Log in to Example <Campus> & "School"'],
            'ILIAS attribution' => ['%s · Powered by ILIAS', 'Example Campus', 'Example Campus · Powered by ILIAS'],
        ];
    }

    #[DataProvider('labels')]
    public function testTranslatedLabelsSubstituteOnlyTheName(
        string $template,
        ?string $configured,
        string $expected
    ): void {
        $this->assertSame($expected, InstanceIdentity::format($template, $configured));
    }
}
